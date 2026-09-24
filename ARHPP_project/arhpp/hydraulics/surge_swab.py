"""Surge & Swab Engine — Burkhardt/Mitchell with HB rheology."""

import math
from dataclasses import dataclass, field
from typing import List

from arhpp.core.constants import (
    PPG_TO_KG_M3, INCH_TO_M, FT_TO_M,
    LBF_100FT2_TO_PA, PA_TO_PSI,
    CLINGING_COEF_A, CLINGING_COEF_B,
)
from arhpp.geometry.well_geometry import effective_hole_id


@dataclass
class SurgeSectionResult:
    top_md: float = 0.0
    bottom_md: float = 0.0
    length_ft: float = 0.0
    hole_id_in: float = 0.0
    pipe_od_in: float = 0.0
    pipe_id_in: float = 0.0
    fluid_id: str = ""
    mw_ppg: float = 0.0
    vp_fps: float = 0.0
    ve_fps: float = 0.0
    clinging_kc: float = 1.0
    tau_w_pa: float = 0.0
    dp_psi: float = 0.0


@dataclass
class SurgeSwabResult:
    total_dp_psi: float = 0.0
    peak_section_dp_psi: float = 0.0
    direction: str = "static"
    closed_end: bool = False
    sections: List[SurgeSectionResult] = field(default_factory=list)


def clinging_factor(dp_in: float, dh_in: float) -> float:
    """Mitchell clinging constant (open-end pipe)."""
    if dh_in <= 0:
        return 1.0
    return CLINGING_COEF_A + CLINGING_COEF_B * (dp_in / dh_in)


def effective_annular_velocity(vp_fps: float, dp_in: float,
                                 di_in: float, dh_in: float,
                                 closed_end: bool = False):
    """
    Returns (Ve_fps, Kc).
    """
    if dh_in <= dp_in or dh_in <= 0:
        return 0.0, 1.0
    denom = dh_in ** 2 - dp_in ** 2
    if closed_end:
        return vp_fps * (dp_in ** 2) / denom, 1.0
    kc = clinging_factor(dp_in, dh_in)
    num = kc * (dp_in ** 2 - di_in ** 2) + di_in ** 2
    return vp_fps * num / denom, kc


def _sec_dp(ve_fps: float, dh_in: float, dp_in: float,
              length_ft: float, mw_ppg: float,
              tau_y: float, k: float, n: float):
    gap_in = dh_in - dp_in
    if gap_in <= 0 or length_ft <= 0 or n <= 0 or abs(ve_fps) < 1e-9:
        return 0.0, 0.0
    gap_m = gap_in * INCH_TO_M
    L_m = length_ft * FT_TO_M
    ve_m = abs(ve_fps) * FT_TO_M
    tau_y_pa = tau_y * LBF_100FT2_TO_PA
    K = k * LBF_100FT2_TO_PA
    gamma_w = (2.0 * n + 1.0) / (3.0 * n) * (12.0 * ve_m / gap_m)
    tau_w = tau_y_pa + K * (gamma_w ** n)
    dp_pa = 4.0 * tau_w * L_m / gap_m
    sign = 1.0 if ve_fps > 0 else -1.0
    return sign * dp_pa * PA_TO_PSI, tau_w


_DP_OD = {}
_DP_ID = {}


def _dp_geom(bha_sections):
    key = id(bha_sections)
    if key in _DP_OD:
        return _DP_OD[key], _DP_ID[key]
    for s in bha_sections:
        if s.component_type == "DP":
            _DP_OD[key] = s.od_in
            _DP_ID[key] = s.id_in
            return s.od_in, s.id_in
    if bha_sections:
        return bha_sections[0].od_in, bha_sections[0].id_in
    return 5.0, 4.276


def _string_geom(bha_sections, md: float, bit_md: float):
    if md > bit_md:
        return 0.0, 0.0
    tail = [s for s in bha_sections if s.component_type != "DP"]
    tail_total = sum(s.length_ft for s in tail)
    tail_top = max(0.0, bit_md - tail_total)
    if md < tail_top:
        return _dp_geom(bha_sections)
    off = md - tail_top
    cum = 0.0
    for s in tail:
        if off <= cum + s.length_ft:
            return s.od_in, s.id_in
        cum += s.length_ft
    if tail:
        return tail[-1].od_in, tail[-1].id_in
    return _dp_geom(bha_sections)


def compute_surge_swab(bit_md: float, vp_fps: float,
                         closed_end: bool, bha_sections,
                         hole_sections, annulus_col, survey,
                         step_ft: float = 30.0) -> SurgeSwabResult:
    """
    Integrate surge/swab along the annulus from surface to bit_md.

    Sign convention:
      +Ve (bit down) -> +dP (surge, increases BHP)
      -Ve (bit up)   -> -dP (swab, decreases BHP)
    """
    res = SurgeSwabResult(closed_end=closed_end)
    if abs(vp_fps) < 1e-9 or bit_md <= 0:
        return res
    res.direction = "surge" if vp_fps > 0 else "swab"
    total = 0.0
    peak = 0.0
    for seg in annulus_col.segments:
        top = seg.top_md
        bot = min(seg.bottom_md, bit_md)
        if bot - top <= 0:
            continue
        md = top
        while md < bot:
            nxt = min(md + step_ft, bot)
            mid = 0.5 * (md + nxt)
            hid = effective_hole_id(hole_sections, mid)
            od, di = _string_geom(bha_sections, mid, bit_md)
            if hid > od > 0:
                ve, kc = effective_annular_velocity(
                    vp_fps, od, di, hid, closed_end)
                dp, tw = _sec_dp(ve, hid, od, nxt - md, seg.mw,
                                  seg.tau_y, seg.k, seg.n)
                res.sections.append(SurgeSectionResult(
                    top_md=md, bottom_md=nxt, length_ft=nxt - md,
                    hole_id_in=hid, pipe_od_in=od, pipe_id_in=di,
                    fluid_id=seg.fluid_id, mw_ppg=seg.mw,
                    vp_fps=vp_fps, ve_fps=ve, clinging_kc=kc,
                    tau_w_pa=tw, dp_psi=dp))
                total += dp
                if abs(dp) > peak:
                    peak = abs(dp)
            md = nxt
    res.total_dp_psi = total
    res.peak_section_dp_psi = peak
    return res
