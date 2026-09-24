"""BHA & String Engine — compute ID/OD per depth, volumes, displacements."""

from typing import List, Optional
from arhpp.core.types import BHASection
from arhpp.core.units import pipe_capacity_bblft, pipe_displacement_bblft


def stack_bha(sections: List[BHASection],
              top_md: float = 0.0) -> List[BHASection]:
    """Assign MD ranges from top down based on length."""
    cur = top_md
    for i, s in enumerate(sections):
        if s.length_ft <= 0:
            raise ValueError(
                f"Section {s.name} (#{i}): length_ft must be > 0, "
                f"got {s.length_ft}"
            )
        if s.od_in <= 0 or s.id_in <= 0:
            raise ValueError(
                f"Section {s.name} (#{i}): OD/ID must be > 0"
            )
        if s.id_in >= s.od_in:
            raise ValueError(
                f"Section {s.name} (#{i}): ID ({s.id_in}) >= "
                f"OD ({s.od_in})"
            )
        s.top_md = cur
        s.bottom_md = cur + s.length_ft
        cur = s.bottom_md
    return sections


def bha_section_at_md(sections: List[BHASection],
                       md: float) -> Optional[BHASection]:
    for s in sections:
        if s.top_md <= md <= s.bottom_md:
            return s
    return None


def string_id_at_md(sections: List[BHASection], md: float) -> float:
    s = bha_section_at_md(sections, md)
    return s.id_in if s else 0.0


def string_od_at_md(sections: List[BHASection], md: float) -> float:
    s = bha_section_at_md(sections, md)
    return s.od_in if s else 0.0


def string_internal_volume_bbl(sections: List[BHASection]) -> float:
    return sum(pipe_capacity_bblft(s.id_in) * s.length_ft for s in sections)


def string_displacement_bbl(sections: List[BHASection]) -> float:
    return sum(
        pipe_displacement_bblft(s.od_in, s.id_in) * s.length_ft
        for s in sections
    )


def string_volume_by_section(sections: List[BHASection]) -> List[dict]:
    out = []
    for s in sections:
        out.append({
            "name": s.name,
            "type": s.component_type,
            "top_md": s.top_md,
            "bottom_md": s.bottom_md,
            "length_ft": s.length_ft,
            "id_in": s.id_in,
            "od_in": s.od_in,
            "capacity_bblft": pipe_capacity_bblft(s.id_in),
            "volume_bbl": pipe_capacity_bblft(s.id_in) * s.length_ft,
            "displacement_bbl": pipe_displacement_bblft(
                s.od_in, s.id_in) * s.length_ft,
        })
    return out
