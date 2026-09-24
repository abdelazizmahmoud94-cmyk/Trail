"""Sigma Method (Total / IFP)."""

from dataclasses import dataclass
from typing import List


@dataclass
class SigmaPoint:
    md_ft: float = 0.0
    tvd_ft: float = 0.0
    sigma: float = 0.0
    is_valid: bool = False


def compute_sigma(rop_ft_hr: float, rpm: float,
                    wob_klb: float, bit_diameter_in: float) -> float:
    """
    Sigma (Total):
      sigma = (WOB / Dbit) / (RPM^0.5 * ROP^0.25)
    """
    if (rop_ft_hr <= 0 or rpm <= 0 or wob_klb <= 0
            or bit_diameter_in <= 0):
        return 0.0
    num = wob_klb / bit_diameter_in
    den = (rpm ** 0.5) * (rop_ft_hr ** 0.25)
    if den <= 0:
        return 0.0
    return num / den


def compute_sigma_series(points) -> List[SigmaPoint]:
    out = []
    for p in points:
        sp = SigmaPoint(md_ft=p.md_ft, tvd_ft=p.tvd_ft)
        if p.rop_ft_hr <= 0 or p.rpm <= 0 or p.wob_klb <= 0:
            out.append(sp)
            continue
        sp.sigma = compute_sigma(
            p.rop_ft_hr, p.rpm, p.wob_klb, p.bit_diameter_in)
        sp.is_valid = sp.sigma > 0
        out.append(sp)
    return out
