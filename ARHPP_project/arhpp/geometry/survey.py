"""Survey Engine — Minimum Curvature + 20 columns (Victus-compatible).

Computed columns:
  MD, Inc, Azi, TVD, TVDSS, North, East,
  L.Distance, DLS, B.Rate, T.Rate, T.Face,
  VS, H.Disp, CL, Tort, ABS Tort, DDI
"""

import math
from typing import List

from arhpp.core.types import SurveyPoint


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def _rf(beta: float) -> float:
    """Ratio factor for minimum curvature."""
    if abs(beta) < 1e-9:
        return 1.0
    return (2.0 / beta) * math.tan(beta / 2.0)


def _wrap_deg(d: float) -> float:
    """Wrap degrees to [-180, 180]."""
    while d > 180.0:
        d -= 360.0
    while d < -180.0:
        d += 360.0
    return d


def _dls_from_beta(beta_rad: float, dmd: float) -> float:
    """DLS in °/100ft."""
    if dmd <= 0:
        return 0.0
    return math.degrees(beta_rad) * 100.0 / dmd


# ═══════════════════════════════════════════════════════════════
#  Main computation
# ═══════════════════════════════════════════════════════════════

def compute_survey(points: List[SurveyPoint],
                   rkb_ft: float = 0.0,
                   target_azi_deg: float = 0.0) -> List[SurveyPoint]:
    """Compute 20 columns for each survey point."""
    if not points:
        return points

    p0 = points[0]
    p0.tvd = p0.md
    p0.tvdss = p0.tvd - rkb_ft
    p0.north = 0.0
    p0.east = 0.0
    p0.l_distance = 0.0
    p0.dls = 0.0
    p0.b_rate = 0.0
    p0.t_rate = 0.0
    p0.t_face = 0.0
    p0.h_disp = 0.0
    p0.closure_length = 0.0
    p0.vs = 0.0
    p0.tortuosity = 0.0
    p0.abs_tortuosity = 0.0
    p0.ddi = 0.0

    target_azi_rad = math.radians(target_azi_deg)

    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]

        i0 = math.radians(prev.inc)
        i1 = math.radians(curr.inc)
        a0 = math.radians(prev.azi)
        a1 = math.radians(curr.azi)

        dmd = curr.md - prev.md
        if dmd <= 0:
            continue

        # Dogleg angle
        cos_beta = (math.cos(i1 - i0)
                    - math.sin(i0) * math.sin(i1) * (1 - math.cos(a1 - a0)))
        cos_beta = max(-1.0, min(1.0, cos_beta))
        beta = math.acos(cos_beta)
        rf = _rf(beta)

        # Position increments
        dtvd = (dmd / 2.0) * (math.cos(i0) + math.cos(i1)) * rf
        dnorth = (dmd / 2.0) * (
            math.sin(i0) * math.cos(a0) + math.sin(i1) * math.cos(a1)
        ) * rf
        deast = (dmd / 2.0) * (
            math.sin(i0) * math.sin(a0) + math.sin(i1) * math.sin(a1)
        ) * rf

        curr.tvd = prev.tvd + dtvd
        curr.north = prev.north + dnorth
        curr.east = prev.east + deast
        curr.tvdss = curr.tvd - rkb_ft

        # L.Distance (chord)
        curr.l_distance = math.sqrt(dtvd ** 2 + dnorth ** 2 + deast ** 2)

        # DLS
        curr.dls = _dls_from_beta(beta, dmd)

        # Build / Turn rate
        dinc_deg = curr.inc - prev.inc
        dazi_deg = _wrap_deg(curr.azi - prev.azi)
        curr.b_rate = dinc_deg * 100.0 / dmd
        curr.t_rate = dazi_deg * 100.0 / dmd

        # Tool Face (0-360, North-referenced, clockwise)
        if abs(curr.b_rate) > 1e-6 or abs(curr.t_rate) > 1e-6:
            tf = math.degrees(math.atan2(curr.t_rate, curr.b_rate))
            curr.t_face = tf % 360.0
        else:
            curr.t_face = 0.0

        # Horizontal displacement
        curr.h_disp = math.sqrt(curr.north ** 2 + curr.east ** 2)
        curr.closure_length = curr.h_disp

        # Vertical section
        curr.vs = (curr.north * math.cos(target_azi_rad)
                   + curr.east * math.sin(target_azi_rad))

        # Tortuosity (cumulative)
        curr.tortuosity = prev.tortuosity + abs(curr.dls) * dmd / 100.0
        curr.abs_tortuosity = abs(curr.tortuosity)

        # DDI (Samuel 2010) — Dogleg Deviation Index
        # DDI = DLS / sqrt(B_rate² + T_rate²)
        if abs(curr.b_rate) > 1e-6 or abs(curr.t_rate) > 1e-6:
            denom = math.sqrt(curr.b_rate ** 2 + curr.t_rate ** 2)
            if denom > 1e-6:
                curr.ddi = curr.dls / denom
            else:
                curr.ddi = 0.0
        else:
            curr.ddi = 0.0

    return points


# Backward compat
def compute_tvd(survey: List[SurveyPoint]) -> List[SurveyPoint]:
    return compute_survey(survey)


def md_to_tvd(survey: List[SurveyPoint], md: float) -> float:
    """Interpolate TVD at a given MD."""
    if not survey:
        return md
    if md <= survey[0].md:
        return survey[0].tvd
    if md >= survey[-1].md:
        return survey[-1].tvd
    for i in range(1, len(survey)):
        if survey[i].md >= md:
            a, b = survey[i - 1], survey[i]
            if b.md == a.md:
                return b.tvd
            f = (md - a.md) / (b.md - a.md)
            return a.tvd + f * (b.tvd - a.tvd)
    return survey[-1].tvd


def tvd_to_md(survey: List[SurveyPoint], tvd: float) -> float:
    """Inverse: MD at given TVD."""
    if not survey:
        return tvd
    for i in range(1, len(survey)):
        if survey[i].tvd >= tvd:
            a, b = survey[i - 1], survey[i]
            if b.tvd == a.tvd:
                return b.md
            f = (tvd - a.tvd) / (b.tvd - a.tvd)
            return a.md + f * (b.md - a.md)
    return survey[-1].md


def survey_to_rows(survey: List[SurveyPoint]) -> List[dict]:
    """Export all 20 columns."""
    return [
        {
            "MD": round(p.md, 2),
            "Inc": round(p.inc, 3),
            "Azi": round(p.azi, 3),
            "TVD": round(p.tvd, 2),
            "TVDSS": round(p.tvdss, 2),
            "North": round(p.north, 3),
            "East": round(p.east, 3),
            "L_Distance": round(p.l_distance, 3),
            "DLS": round(p.dls, 4),
            "B_Rate": round(p.b_rate, 4),
            "T_Rate": round(p.t_rate, 4),
            "T_Face": round(p.t_face, 2),
            "VS": round(p.vs, 3),
            "H_Disp": round(p.h_disp, 3),
            "CL": round(p.closure_length, 3),
            "Tort": round(p.tortuosity, 4),
            "ABS_Tort": round(p.abs_tortuosity, 4),
            "DDI": round(p.ddi, 4),
            "Comments": p.comments,
        }
        for p in survey
    ]
