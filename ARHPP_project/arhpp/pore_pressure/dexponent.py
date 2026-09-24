"""D-Exponent + Corrected D-Exponent (Rehm & McClendon)."""

import math
from dataclasses import dataclass
from typing import List

from arhpp.core.constants import (
    MW_NORMAL_PPG, DC_MIN_VALID, DC_MAX_VALID,
)


@dataclass
class DrillingPoint:
    md_ft: float = 0.0
    tvd_ft: float = 0.0
    rop_ft_hr: float = 0.0
    rpm: float = 0.0
    wob_klb: float = 0.0
    bit_diameter_in: float = 8.5
    mw_ppg: float = 10.0
    torque_ftlb: float = 0.0
    spp_psi: float = 0.0


@dataclass
class DExponentResult:
    md_ft: float = 0.0
    tvd_ft: float = 0.0
    d_exp: float = 0.0
    dc_exp: float = 0.0
    dc_norm: float = 0.0
    is_valid: bool = False
    reason: str = ""


def compute_d_exponent(rop_ft_hr: float, rpm: float,
                        wob_klb: float, bit_diameter_in: float) -> float:
    """
    Standard d-exponent (Bourgoyne):
      d = log10(ROP / (60*RPM)) / log10(WOB / Dbit)
    """
    if rop_ft_hr <= 0 or rpm <= 0 or wob_klb <= 0 or bit_diameter_in <= 0:
        return 0.0
    num = math.log10(rop_ft_hr / (60.0 * rpm))
    den = math.log10((12.0 * wob_klb * 1000.0) / (1_000_000.0 * bit_diameter_in))
    if abs(den) < 1e-9:
        return 0.0
    return num / den


def correct_d_exponent_mw(d_exp: float, mw_ppg: float,
                            mw_normal_ppg: float = MW_NORMAL_PPG) -> float:
    """Rehm & McClendon MW correction: dc = d * (MW_normal / MW_actual)."""
    if mw_ppg <= 0:
        return d_exp
    return d_exp * (mw_normal_ppg / mw_ppg)


def normalize_d_exponent_tvd(dc: float, tvd_ft: float,
                                tvd_normal_ft: float = 1000.0) -> float:
    """TVD normalization: dcn = dc * (TVD_normal / TVD_actual)."""
    if tvd_ft <= 0:
        return dc
    return dc * (tvd_normal_ft / tvd_ft)


def compute_dexponent_series(points: List[DrillingPoint],
                                mw_normal_ppg: float = MW_NORMAL_PPG
                                ) -> List[DExponentResult]:
    out: List[DExponentResult] = []
    for p in points:
        r = DExponentResult(md_ft=p.md_ft, tvd_ft=p.tvd_ft)
        if p.rop_ft_hr <= 0 or p.rpm <= 0 or p.wob_klb <= 0:
            r.reason = "missing drilling parameters"
            out.append(r)
            continue
        d = compute_d_exponent(
            p.rop_ft_hr, p.rpm, p.wob_klb, p.bit_diameter_in)
        if not (DC_MIN_VALID <= d <= DC_MAX_VALID):
            r.reason = f"d out of range: {d:.2f}"
            out.append(r)
            continue
        dc = correct_d_exponent_mw(d, p.mw_ppg, mw_normal_ppg)
        dcn = normalize_d_exponent_tvd(dc, p.tvd_ft)
        r.d_exp = d
        r.dc_exp = dc
        r.dc_norm = dcn
        r.is_valid = True
        out.append(r)
    return out
