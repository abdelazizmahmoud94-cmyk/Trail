"""Multi-Fluid Tracking — the backbone of ARHPP hydrostatic accuracy."""

from typing import List

from arhpp.core.types import FluidSegment
from arhpp.geometry.survey import md_to_tvd
from arhpp.core.units import pipe_capacity_bblft, annulus_capacity_bblft


class FluidColumn:
    """Stack of immiscible fluid segments in a conduit."""

    def __init__(self, segments: List[FluidSegment]):
        self.segments = sorted(segments, key=lambda s: s.top_md)
        self._validate()

    def _validate(self):
        # Ordering per segment
        for i, seg in enumerate(self.segments):
            if seg.top_md < 0:
                raise ValueError(
                    f"Segment {seg.fluid_id}: top_md must be >= 0")
            if seg.bottom_md <= seg.top_md:
                raise ValueError(
                    f"Segment {seg.fluid_id}: bottom_md ({seg.bottom_md}) "
                    f"must be > top_md ({seg.top_md})")
        # Continuity
        for i in range(1, len(self.segments)):
            a, b = self.segments[i - 1], self.segments[i]
            if abs(b.top_md - a.bottom_md) > 1e-3:
                raise ValueError(
                    f"Gap between segments: "
                    f"{a.fluid_id} ends at {a.bottom_md}, "
                    f"{b.fluid_id} starts at {b.top_md}")

    def at_md(self, md: float) -> FluidSegment | None:
        for s in self.segments:
            if s.top_md <= md <= s.bottom_md:
                return s
        return None

    def total_volume(self) -> float:
        return sum(s.volume_bbl for s in self.segments)

    def assign_tvd(self, survey):
        for s in self.segments:
            s.top_tvd = md_to_tvd(survey, s.top_md)
            s.bottom_tvd = md_to_tvd(survey, s.bottom_md)


def compute_segment_volume(top_md: float, bottom_md: float,
                             capacity_bblft: float) -> float:
    return capacity_bblft * (bottom_md - top_md)


def build_string_column(raw_segments: List[dict],
                          string_id_lookup,
                          survey) -> FluidColumn:
    """raw_segments = [{fluid_id, mw, top_md, bottom_md}, ...]"""
    segs = []
    for r in raw_segments:
        mid = (r["top_md"] + r["bottom_md"]) / 2.0
        cap = pipe_capacity_bblft(string_id_lookup(mid))
        seg = FluidSegment(
            fluid_id=r["fluid_id"],
            mw=r["mw"],
            top_md=r["top_md"],
            bottom_md=r["bottom_md"],
            volume_bbl=compute_segment_volume(
                r["top_md"], r["bottom_md"], cap),
        )
        segs.append(seg)
    col = FluidColumn(segs)
    col.assign_tvd(survey)
    return col


def build_annulus_column(raw_segments: List[dict],
                           hole_id_lookup,
                           string_od_lookup,
                           survey) -> FluidColumn:
    segs = []
    for r in raw_segments:
        mid = (r["top_md"] + r["bottom_md"]) / 2.0
        cap = annulus_capacity_bblft(
            hole_id_lookup(mid), string_od_lookup(mid))
        seg = FluidSegment(
            fluid_id=r["fluid_id"],
            mw=r["mw"],
            top_md=r["top_md"],
            bottom_md=r["bottom_md"],
            volume_bbl=compute_segment_volume(
                r["top_md"], r["bottom_md"], cap),
        )
        segs.append(seg)
    col = FluidColumn(segs)
    col.assign_tvd(survey)
    return col
