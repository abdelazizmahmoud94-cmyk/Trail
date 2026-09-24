"""Buckling Engine — Paslay-Dawson with Mitchell curvature correction."""

import math
from dataclasses import dataclass
from typing import Optional

from arhpp.mechanics.types import BucklingType, TDConfig


DEG_TO_RAD = math.pi / 180.0


@dataclass
class BucklingThreshold:
    sinusoidal_threshold_klb: float = 0.0
    helical_threshold_klb: float = 0.0
    buckling_type: BucklingType = BucklingType.NONE
    critical_force_klb: float = 0.0
    note: str = ""


class BucklingEngine:
    def __init__(self, config: Optional[TDConfig] = None):
        self.config = config or TDConfig()

    def check_buckling(self, od_in: float, id_in: float,
                         inc_deg: float, dls: float,
                         axial_load_klb: float,
                         mw_ppg: float = 12.0,
                         hole_id_in: float = 8.5) -> BucklingThreshold:
        result = BucklingThreshold()
        area_in2 = math.pi / 4.0 * (od_in ** 2 - id_in ** 2)
        if area_in2 <= 0:
            return result
        I_in4 = math.pi / 64.0 * (od_in ** 4 - id_in ** 4)
        E = self.config.tubular_youngs_psi
        bf = 1.0 - mw_ppg / self.config.tubular_density_ppg
        w_lb_ft = area_in2 * 12.0 * self.config.tubular_density_ppg / 231.0
        w_lb_in = w_lb_ft * bf / 12.0
        r_c_in = max((hole_id_in - od_in) / 2.0, 0.05)

        inc_rad = inc_deg * DEG_TO_RAD
        sin_inc = max(math.sin(inc_rad), 0.05)

        # Mitchell (1996) curvature correction
        dls_rad_per_in = dls * DEG_TO_RAD / 100.0 / 12.0
        kappa_effect = r_c_in * dls_rad_per_in
        sin_inc_eff = sin_inc + kappa_effect

        F_sin_lb = 2.0 * math.sqrt(
            E * I_in4 * w_lb_in * sin_inc_eff / r_c_in)
        F_sin_klb = F_sin_lb / 1000.0
        F_hel_klb = F_sin_klb * 1.46

        result.sinusoidal_threshold_klb = F_sin_klb
        result.helical_threshold_klb = F_hel_klb
        result.critical_force_klb = F_sin_klb

        if axial_load_klb >= F_hel_klb:
            result.buckling_type = BucklingType.HELICAL
            result.note = "Helical buckling - reduce WOB"
        elif axial_load_klb >= F_sin_klb:
            result.buckling_type = BucklingType.SINUSOIDAL
            result.note = "Sinusoidal buckling"
        else:
            result.buckling_type = BucklingType.NONE
            result.note = "No buckling"
        return result

    def critical_wob_klb(self, od_in: float, id_in: float,
                            inc_deg: float, dls: float,
                            mw_ppg: float,
                            hole_id_in: float = 8.5):
        th = self.check_buckling(
            od_in=od_in, id_in=id_in, inc_deg=inc_deg, dls=dls,
            axial_load_klb=0.0, mw_ppg=mw_ppg, hole_id_in=hole_id_in)
        return th.sinusoidal_threshold_klb, th.helical_threshold_klb
