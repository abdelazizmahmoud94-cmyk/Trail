"""Aggregate volumes for the well."""

from typing import List
from arhpp.core.types import HoleSection, BHASection
from arhpp.geometry import well_geometry as wg
from arhpp.geometry import bha as bha_mod


def annular_volume_bbl(sections: List[HoleSection],
                        bha: List[BHASection]) -> float:
    """Integrate annular capacity over MD with 30-ft steps."""
    total = 0.0
    for s in sections:
        md, bot = s.top_md, s.bottom_md
        step = 30.0
        while md < bot:
            nxt = min(md + step, bot)
            hid = wg.effective_hole_id(sections, (md + nxt) / 2.0)
            od = bha_mod.string_od_at_md(bha, (md + nxt) / 2.0)
            if hid > od > 0:
                total += (hid ** 2 - od ** 2) / 1029.4 * (nxt - md)
            md = nxt
    return total


def well_volume_report(sections: List[HoleSection],
                        bha: List[BHASection]) -> dict:
    return {
        "string_internal_bbl": bha_mod.string_internal_volume_bbl(bha),
        "string_displacement_bbl": bha_mod.string_displacement_bbl(bha),
        "annular_bbl": annular_volume_bbl(sections, bha),
        "open_hole_bbl": wg.open_hole_volume_bbl(sections),
        "cased_hole_bbl": wg.cased_hole_volume_bbl(sections),
    }
