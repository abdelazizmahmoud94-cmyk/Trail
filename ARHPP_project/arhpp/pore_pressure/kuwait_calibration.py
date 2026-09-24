"""Kuwait Field Calibration – RA-0915 EOWR (real field data)."""

import bisect
from dataclasses import dataclass
from typing import Optional, List

from arhpp.core.constants import KUWAIT_RA0915_FORMATIONS


@dataclass
class KuwaitFormation:
    name: str
    md_top_ft: float
    tvd_top_ft: float
    pp_gradient_ppg: float
    fg_gradient_ppg: float
    mw_used_ppg: float
    lithology: str = "carbonate"
    notes: str = ""


@dataclass
class FormationContext:
    name: str = ""
    depth_into_ft: float = 0.0
    pp_reference_ppg: float = 8.65
    fg_reference_ppg: float = 14.0
    mw_used_ppg: float = 10.0
    pp_margin_ppg: float = 0.5
    fg_margin_ppg: float = 0.5
    lithology: str = ""
    notes: str = ""


_LITHO = {
    "Zubair": "sandstone/shale",
    "Ratawi": "limestone/shale",
    "Minagish": "limestone",
    "Makhul": "limestone",
    "Hith": "anhydrite",
    "Gotnia": "anhydrite/salt",
    "Najmah": "limestone/shale",
    "Sargelu": "limestone",
    "Dharuma": "shale/limestone",
    "Marrat": "limestone/dolomite/shale",
}


def _litho(name: str) -> str:
    for k, v in _LITHO.items():
        if k.lower() in name.lower():
            return v
    return "carbonate"


FORMATIONS: List[KuwaitFormation] = [
    KuwaitFormation(
        name=n, md_top_ft=md, tvd_top_ft=tvd,
        pp_gradient_ppg=pp, fg_gradient_ppg=fg,
        mw_used_ppg=mw, lithology=_litho(n), notes=notes,
    )
    for (n, md, tvd, pp, fg, mw, notes) in KUWAIT_RA0915_FORMATIONS
]
FORMATION_TOPS_MD = [f.md_top_ft for f in FORMATIONS]


def formation_at_md(md_ft: float) -> Optional[KuwaitFormation]:
    if not FORMATIONS or md_ft < FORMATION_TOPS_MD[0]:
        return None
    idx = bisect.bisect_right(FORMATION_TOPS_MD, md_ft) - 1
    if 0 <= idx < len(FORMATIONS):
        return FORMATIONS[idx]
    return None


def formation_context(md_ft: float, tvd_ft: float) -> FormationContext:
    f = formation_at_md(md_ft)
    if f is None:
        return FormationContext()
    return FormationContext(
        name=f.name,
        depth_into_ft=max(0.0, md_ft - f.md_top_ft),
        pp_reference_ppg=f.pp_gradient_ppg,
        fg_reference_ppg=f.fg_gradient_ppg,
        mw_used_ppg=f.mw_used_ppg,
        pp_margin_ppg=0.5,
        fg_margin_ppg=0.5,
        lithology=f.lithology,
        notes=f.notes,
    )


def _interp(md_ft: float, attr: str) -> float:
    if not FORMATIONS:
        return 8.65 if attr == "pp" else 14.0
    if md_ft <= FORMATIONS[0].md_top_ft:
        return getattr(FORMATIONS[0], f"{attr}_gradient_ppg")
    if md_ft >= FORMATIONS[-1].md_top_ft:
        return getattr(FORMATIONS[-1], f"{attr}_gradient_ppg")
    idx = bisect.bisect_right(FORMATION_TOPS_MD, md_ft) - 1
    a = FORMATIONS[idx]
    b = FORMATIONS[min(idx + 1, len(FORMATIONS) - 1)]
    span = max(b.md_top_ft - a.md_top_ft, 1e-6)
    f = (md_ft - a.md_top_ft) / span
    va = getattr(a, f"{attr}_gradient_ppg")
    vb = getattr(b, f"{attr}_gradient_ppg")
    return va + f * (vb - va)


def pp_ppg_at_md(md_ft: float, tvd_ft: float) -> float:
    return _interp(md_ft, "pp")


def fg_ppg_at_md(md_ft: float, tvd_ft: float) -> float:
    return _interp(md_ft, "fg")


def mw_used_at_md(md_ft: float) -> float:
    if not FORMATIONS:
        return 10.0
    idx = bisect.bisect_right(FORMATION_TOPS_MD, md_ft) - 1
    idx = max(0, min(idx, len(FORMATIONS) - 1))
    return FORMATIONS[idx].mw_used_ppg


def drilling_window(md_ft: float, tvd_ft: float) -> dict:
    pp = pp_ppg_at_md(md_ft, tvd_ft)
    fg = fg_ppg_at_md(md_ft, tvd_ft)
    return {
        "pp_ppg": pp,
        "fg_ppg": fg,
        "mw_min_ppg": pp + 0.3,
        "mw_max_ppg": max(pp + 0.3, fg - 0.3),
        "window_width_ppg": max(0.0, fg - pp - 0.6),
    }


def kuwait_table() -> List[dict]:
    return [
        {
            "Name": f.name,
            "MD_top_ft": f.md_top_ft,
            "TVD_top_ft": f.tvd_top_ft,
            "PP_ref_ppg": f.pp_gradient_ppg,
            "FG_ref_ppg": f.fg_gradient_ppg,
            "MW_used_ppg": f.mw_used_ppg,
            "Lithology": f.lithology,
            "Notes": f.notes,
        }
        for f in FORMATIONS
    ]
