"""Hydrostatic Engine — segment-wise, not single MW."""

from arhpp.core.constants import PSI_PER_FT_PER_PPG
from arhpp.geometry.survey import md_to_tvd


def hydrostatic_segment(mw_ppg: float,
                          tvd_top: float,
                          tvd_bottom: float) -> float:
    """Ph = 0.052 * MW * delta_TVD."""
    return PSI_PER_FT_PER_PPG * mw_ppg * (tvd_bottom - tvd_top)


def hydrostatic_column_detailed(segments, survey) -> dict:
    """Per-segment breakdown + total."""
    rows = []
    total = 0.0
    for s in segments:
        t_t = s.top_tvd or md_to_tvd(survey, s.top_md)
        t_b = s.bottom_tvd or md_to_tvd(survey, s.bottom_md)
        ph = hydrostatic_segment(s.mw, t_t, t_b)
        total += ph
        rows.append({
            "fluid_id": s.fluid_id,
            "mw_ppg": s.mw,
            "top_md": s.top_md,
            "bottom_md": s.bottom_md,
            "top_tvd": t_t,
            "bottom_tvd": t_b,
            "volume_bbl": s.volume_bbl,
            "ph_psi": ph,
        })
    return {"total_psi": total, "segments": rows}


def full_hydrostatic(string_col, annulus_col, survey) -> dict:
    s = hydrostatic_column_detailed(string_col.segments, survey)
    a = hydrostatic_column_detailed(annulus_col.segments, survey)
    return {
        "string": s,
        "annulus": a,
        "utube_dp_psi": s["total_psi"] - a["total_psi"],
    }
