"""Well Geometry Engine — hole, casing, sections."""

from typing import List, Optional
from arhpp.core.types import HoleSection
from arhpp.core.units import pipe_capacity_bblft


def hole_section_at_md(sections: List[HoleSection],
                        md: float) -> Optional[HoleSection]:
    for s in sections:
        if s.top_md <= md <= s.bottom_md:
            return s
    return None


def effective_hole_id(sections: List[HoleSection], md: float) -> float:
    """Open hole if below casing shoe, otherwise casing ID."""
    s = hole_section_at_md(sections, md)
    if s is None:
        return 0.0
    if (s.casing_id_in and s.casing_shoe_md is not None
            and md < s.casing_shoe_md):
        return s.casing_id_in
    return s.hole_id_in


def open_hole_volume_bbl(sections: List[HoleSection]) -> float:
    total = 0.0
    for s in sections:
        if s.casing_shoe_md is not None and s.casing_shoe_md < s.bottom_md:
            oh_top = max(s.top_md, s.casing_shoe_md)
            length = s.bottom_md - oh_top
            if length > 0:
                total += pipe_capacity_bblft(s.hole_id_in) * length
        else:
            total += pipe_capacity_bblft(s.hole_id_in) * (
                s.bottom_md - s.top_md)
    return total


def cased_hole_volume_bbl(sections: List[HoleSection]) -> float:
    total = 0.0
    for s in sections:
        if s.casing_id_in and s.casing_shoe_md is not None:
            length = min(s.casing_shoe_md, s.bottom_md) - s.top_md
            if length > 0:
                total += pipe_capacity_bblft(s.casing_id_in) * length
    return total
