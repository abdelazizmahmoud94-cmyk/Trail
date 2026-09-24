"""ARHPP — Core data types."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class SurveyPoint:
    md: float = 0.0
    inc: float = 0.0
    azi: float = 0.0
    tvd: float = 0.0
    tvdss: float = 0.0
    north: float = 0.0
    east: float = 0.0
    l_distance: float = 0.0
    dls: float = 0.0
    b_rate: float = 0.0
    t_rate: float = 0.0
    t_face: float = 0.0
    vs: float = 0.0
    h_disp: float = 0.0
    closure_length: float = 0.0
    tortuosity: float = 0.0
    abs_tortuosity: float = 0.0
    ddi: float = 0.0
    comments: str = ""


@dataclass
class HoleSection:
    name: str
    hole_id_in: float
    top_md: float
    bottom_md: float
    casing_od_in: Optional[float] = None
    casing_id_in: Optional[float] = None
    casing_shoe_md: Optional[float] = None


@dataclass
class BHASection:
    name: str
    component_type: str
    od_in: float
    id_in: float
    length_ft: float
    top_md: float = 0.0
    bottom_md: float = 0.0


@dataclass
class FluidSegment:
    fluid_id: str
    mw: float
    top_md: float
    bottom_md: float
    volume_bbl: float = 0.0
    top_tvd: float = 0.0
    bottom_tvd: float = 0.0
    pv: float = 0.0
    yp: float = 0.0
    n: float = 1.0
    k: float = 0.0
    tau_y: float = 0.0
    gel_10s: float = 0.0
    gel_10min: float = 0.0
    gel_30min: float = 0.0
    temp_f: float = 125.0


@dataclass
class PressureLedger:
    """Pressure decomposition — no correction factors."""
    hydrostatic_string: float = 0.0
    hydrostatic_annulus: float = 0.0
    pipe_friction: float = 0.0
    annular_friction: float = 0.0
    bit_dp: float = 0.0
    sbp: float = 0.0
    utube: float = 0.0
    surge: float = 0.0
    swab: float = 0.0
    gas_effect: float = 0.0
    loss_effect: float = 0.0
    kick_effect: float = 0.0
    bhp: float = 0.0
    ecd: float = 0.0
    tvd_ref: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return self.__dict__.copy()


@dataclass
class WellHeader:
    well_name: str = "WELL-1"
    rig_name: str = ""
    field: str = ""
    rkb_ft: float = 0.0
    water_depth_ft: float = 0.0
    datum: str = "RKB"
    operator: str = ""
    country: str = "Kuwait"
