"""Multi-Fluid Engine — Manage multiple fluids (A, B, C)."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from copy import deepcopy


@dataclass
class FluidSpec:
    """Full specification of one fluid."""
    id: str = "MUD-A"
    name: str = "Mud A"
    fluid_type: str = "OBM"

    mw_ppg: float = 10.0
    density_temp_coeff: float = -0.00035
    compressibility: float = 4.5e-6

    pv_cp: float = 30.0
    yp_lbf100: float = 15.0
    lsyp: float = 7.0
    n_hb: float = 0.7
    k_hb: float = 0.5
    tau_y: float = 8.0

    r600: float = 52.0
    r300: float = 30.0
    r200: float = 21.0
    r100: float = 13.0
    r6: float = 5.0
    r3: float = 4.0

    gel_10s: float = 8.0
    gel_10min: float = 18.0
    gel_30min: float = 21.0

    oil_pct: float = 52.0
    water_pct: float = 11.0
    solids_pct: float = 27.5
    oil_water_ratio: str = "83/17"

    thermal_conductivity: float = 0.61
    specific_heat: float = 0.33
    api_fluid_loss: float = 0.0
    hthp_fluid_loss: float = 3.5
    cake_api: float = 0.0
    ph: float = 8.5
    cl_whole_mud: float = 31000.0
    salt_pct: float = 30.61
    lime_lb_bbl: float = 1.82
    emul_stability: float = 710.0
    mud_temp_in_f: float = 115.0

    # Derived
    bit_loss_psi: float = 0.0
    bit_loss_pct: float = 0.0
    bit_hhp: float = 0.0
    bit_hsi: float = 0.0
    jet_velocity_fps: float = 0.0
    va_pipe_fpm: float = 0.0
    va_collars_fpm: float = 0.0
    cva_pipe_fpm: float = 0.0
    cva_collars_fpm: float = 0.0


@dataclass
class FluidSegmentAssignment:
    """Assign a fluid to an MD range."""
    fluid_id: str
    top_md: float
    bottom_md: float
    location: str = "annulus"


class MultiFluidSystem:
    """Multi-fluid manager."""

    def __init__(self):
        self._fluids: Dict[str, FluidSpec] = {}
        self._string_segments: List[FluidSegmentAssignment] = []
        self._annulus_segments: List[FluidSegmentAssignment] = []
        self._active_fluid_id: Optional[str] = None

    def add_fluid(self, spec: FluidSpec) -> None:
        self._fluids[spec.id] = spec
        if self._active_fluid_id is None:
            self._active_fluid_id = spec.id

    def get_fluid(self, fluid_id: str) -> Optional[FluidSpec]:
        return self._fluids.get(fluid_id)

    def list_fluids(self) -> List[FluidSpec]:
        return list(self._fluids.values())

    def set_active_fluid(self, fluid_id: str) -> None:
        if fluid_id not in self._fluids:
            raise KeyError(f"Unknown fluid: {fluid_id}")
        self._active_fluid_id = fluid_id

    def active_fluid(self) -> Optional[FluidSpec]:
        if self._active_fluid_id is None:
            return None
        return self._fluids.get(self._active_fluid_id)

    def clone_fluid(self, src_id: str, new_id: str,
                     new_name: Optional[str] = None,
                     overrides: Optional[Dict] = None) -> FluidSpec:
        if src_id not in self._fluids:
            raise KeyError(f"Source fluid not found: {src_id}")
        new_spec = deepcopy(self._fluids[src_id])
        new_spec.id = new_id
        new_spec.name = new_name or f"{new_spec.name} (copy)"
        if overrides:
            for k, v in overrides.items():
                if hasattr(new_spec, k):
                    setattr(new_spec, k, v)
        self._fluids[new_id] = new_spec
        return new_spec

    def set_string_segments(self,
                              segments: List[FluidSegmentAssignment]) -> None:
        self._string_segments = sorted(segments, key=lambda x: x.top_md)
        self._validate_segments(self._string_segments)

    def set_annulus_segments(self,
                               segments: List[FluidSegmentAssignment]) -> None:
        self._annulus_segments = sorted(segments, key=lambda x: x.top_md)
        self._validate_segments(self._annulus_segments)

    @staticmethod
    def _validate_segments(segments):
        for i in range(1, len(segments)):
            a, b = segments[i - 1], segments[i]
            if abs(b.top_md - a.bottom_md) > 1e-3:
                raise ValueError(
                    f"Gap between segments: "
                    f"{a.fluid_id} ends {a.bottom_md}, "
                    f"{b.fluid_id} starts {b.top_md}"
                )

    def string_segments(self):
        return list(self._string_segments)

    def annulus_segments(self):
        return list(self._annulus_segments)

    def fluid_at_md(self, md: float, location: str = "annulus"):
        segs = (self._annulus_segments if location == "annulus"
                else self._string_segments)
        for s in segs:
            if s.top_md <= md <= s.bottom_md:
                return self._fluids.get(s.fluid_id)
        return None

    def displace_annulus(self, new_fluid_id: str,
                           pump_rate_gpm: float,
                           elapsed_min: float,
                           hole_id_in: float,
                           pipe_od_in: float) -> Dict:
        if new_fluid_id not in self._fluids:
            raise KeyError(f"Unknown fluid: {new_fluid_id}")
        cap_bblft = (hole_id_in ** 2 - pipe_od_in ** 2) / 1029.4
        vol_pumped_bbl = (pump_rate_gpm / 42.0) * elapsed_min
        front_ft = vol_pumped_bbl / cap_bblft if cap_bblft > 0 else 0.0
        return {
            "new_fluid_id": new_fluid_id,
            "volume_pumped_bbl": round(vol_pumped_bbl, 2),
            "front_md_ft": round(front_ft, 2),
            "capacity_bblft": round(cap_bblft, 5),
        }

    def summary(self) -> Dict:
        return {
            "n_fluids": len(self._fluids),
            "active": self._active_fluid_id,
            "fluids": [
                {
                    "id": f.id, "name": f.name, "type": f.fluid_type,
                    "mw_ppg": f.mw_ppg, "n": f.n_hb, "k": f.k_hb,
                    "tau_y": f.tau_y,
                }
                for f in self._fluids.values()
            ],
            "string_segments": [
                {"fluid": s.fluid_id, "top": s.top_md, "bottom": s.bottom_md}
                for s in self._string_segments
            ],
            "annulus_segments": [
                {"fluid": s.fluid_id, "top": s.top_md, "bottom": s.bottom_md}
                for s in self._annulus_segments
            ],
        }


def build_from_well_info(mud_a_row: Dict,
                            mud_b_row: Dict) -> MultiFluidSystem:
    """Build MultiFluidSystem from Excel rows."""
    sys = MultiFluidSystem()

    def _f(row, *keys, default=0.0):
        for k in keys:
            if k in row and row[k] not in (None, ""):
                try:
                    return float(row[k])
                except (ValueError, TypeError):
                    pass
        return default

    def _s(row, *keys, default=""):
        for k in keys:
            if k in row and row[k] not in (None, ""):
                return str(row[k])
        return default

    a = FluidSpec(
        id="MUD-A", name="Mud A",
        fluid_type=_s(mud_a_row, "Mud Type", default="OBM"),
        mw_ppg=_f(mud_a_row, "Mud Weight", "MW", default=10.0),
        pv_cp=_f(mud_a_row, "PV", default=30.0),
        yp_lbf100=_f(mud_a_row, "YP", default=15.0),
        n_hb=_f(mud_a_row, "n", default=0.7),
        k_hb=_f(mud_a_row, "k", default=0.5),
        tau_y=_f(mud_a_row, "TauY", default=8.0),
    )
    b = FluidSpec(
        id="MUD-B", name="Mud B",
        fluid_type=_s(mud_b_row, "Mud Type", default="OBM"),
        mw_ppg=_f(mud_b_row, "Mud Weight", "MW", default=10.0),
        pv_cp=_f(mud_b_row, "PV", default=30.0),
        yp_lbf100=_f(mud_b_row, "YP", default=15.0),
        n_hb=_f(mud_b_row, "n", default=0.7),
        k_hb=_f(mud_b_row, "k", default=0.5),
        tau_y=_f(mud_b_row, "TauY", default=8.0),
    )
    sys.add_fluid(a)
    sys.add_fluid(b)
    sys.set_active_fluid("MUD-A")
    return sys
