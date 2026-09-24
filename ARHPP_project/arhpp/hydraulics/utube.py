"""U-Tube Engine — delta_P as a *flow driver*, not a correction."""

import math
from dataclasses import dataclass

from arhpp.core.constants import (
    PSI_PER_FT_PER_PPG, INCH_TO_M, FT_TO_M,
    GPM_TO_M3S, LBF_100FT2_TO_PA,
)
from arhpp.geometry.well_geometry import effective_hole_id
from arhpp.geometry.bha import string_od_at_md


@dataclass
class UTubeResult:
    ph_string: float = 0.0
    ph_annulus: float = 0.0
    dp_utube_psi: float = 0.0
    flow_direction: str = "static"
    q_utube_gpm: float = 0.0
    severity_index: float = 0.0
    is_significant: bool = False


def _severity(dp_psi: float, tvd_ft: float) -> float:
    ref = PSI_PER_FT_PER_PPG * 1.0 * max(tvd_ft, 1.0)
    return min(1.0, abs(dp_psi) / ref) if ref > 0 else 0.0


def _eq_length(string_col, annulus_col) -> float:
    s = string_col.segments[-1].bottom_tvd if string_col.segments else 0.0
    a = annulus_col.segments[-1].bottom_tvd if annulus_col.segments else 0.0
    return max(s, a, 1.0)


def _eq_gap(bha_sections, hole_sections,
              string_col, annulus_col) -> float:
    if not annulus_col.segments:
        return 1.0
    tw = 0.0
    gw = 0.0
    for seg in annulus_col.segments:
        span = max(seg.bottom_tvd - seg.top_tvd, 1.0)
        mid = 0.5 * (seg.top_md + seg.bottom_md)
        hid = effective_hole_id(hole_sections, mid)
        od = string_od_at_md(bha_sections, mid)
        gw += max(hid - od, 0.1) * span
        tw += span
    return gw / tw if tw > 0 else 1.0


def _flow_from_dp(dp_psi, length_ft, gap_in, mw_ppg,
                    tau_y, k, n) -> float:
    """Solve Q_utube (gpm) from dP for HB fluid in annular slot."""
    if abs(dp_psi) < 1e-6 or length_ft <= 0 or gap_in <= 0 or n <= 0:
        return 0.0
    dp_pa = abs(dp_psi) * 6894.757
    L_m = length_ft * FT_TO_M
    gap_m = gap_in * INCH_TO_M
    tau_y_pa = tau_y * LBF_100FT2_TO_PA
    K = k * LBF_100FT2_TO_PA
    dpdl = dp_pa / L_m
    dpdl_yield = 2.0 * tau_y_pa / gap_m
    if dpdl <= dpdl_yield:
        return 0.0
    V = 0.5
    for _ in range(80):
        gamma = (2.0 * n + 1.0) / (3.0 * n) * (12.0 * V / gap_m)
        tau_w = tau_y_pa + K * gamma ** n
        dpdl_calc = 2.0 * tau_w / gap_m
        if dpdl_calc <= 0:
            break
        V *= (dpdl / dpdl_calc) ** (1.0 / max(n, 0.1))
        V = max(1e-4, min(V, 100.0))
        if abs(dpdl_calc - dpdl) / dpdl < 1e-4:
            break
    area = math.pi * gap_m * (gap_m * 10)
    q_gpm = (V * area) / GPM_TO_M3S
    return q_gpm if dp_psi > 0 else -q_gpm


def compute_utube(string_col, annulus_col, bha_sections, hole_sections,
                    utube_enabled: bool = True,
                    choke_closed: bool = False) -> UTubeResult:
    """
    U-Tube as flow driver.

    Sign convention:
      +dP (Ph_string > Ph_annulus) -> forward flow (string -> annulus)
    """
    r = UTubeResult()
    r.ph_string = sum(
        PSI_PER_FT_PER_PPG * s.mw * (s.bottom_tvd - s.top_tvd)
        for s in string_col.segments
    )
    r.ph_annulus = sum(
        PSI_PER_FT_PER_PPG * s.mw * (s.bottom_tvd - s.top_tvd)
        for s in annulus_col.segments
    )
    r.dp_utube_psi = r.ph_string - r.ph_annulus

    tvd_ref = _eq_length(string_col, annulus_col)
    mw_ref = string_col.segments[-1].mw if string_col.segments else 10.0
    r.severity_index = _severity(r.dp_utube_psi, tvd_ref)

    if choke_closed or not utube_enabled or abs(r.dp_utube_psi) < 1.0:
        return r

    bot = string_col.segments[-1] if string_col.segments else None
    tau_y = getattr(bot, "tau_y", 0.0) if bot else 0.0
    k = getattr(bot, "k", 0.0) if bot else 0.0
    n = getattr(bot, "n", 1.0) if bot else 1.0
    gap = _eq_gap(bha_sections, hole_sections, string_col, annulus_col)

    # U-Tube is a CLOSED LOOP:
    #   1. Down the string (length = TVD)
    #   2. Up the annulus (length = TVD)
    # Total effective path = 2 * TVD (round-trip)
    tvd_path = _eq_length(string_col, annulus_col)
    L_total_ft = tvd_path * 2.0

    q = _flow_from_dp(r.dp_utube_psi, L_total_ft, gap, mw_ref,
                       tau_y, k, n)

    r.q_utube_gpm = q
    if q > 0.5:
        r.flow_direction = "forward"
    elif q < -0.5:
        r.flow_direction = "reverse"
    else:
        r.flow_direction = "static"
    r.is_significant = abs(q) > 5.0
    return r
