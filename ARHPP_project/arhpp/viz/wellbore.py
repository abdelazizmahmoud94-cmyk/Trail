"""Wellbore Schematic — 2D section view."""

import math
from dataclasses import dataclass, field
from typing import List


@dataclass
class SchematicSection:
    name: str
    kind: str
    top_md: float
    bottom_md: float
    id_in: float
    od_in: float = 0.0
    color: str = "#78909c"
    weight_ppf: float = 0.0
    grade: str = ""


@dataclass
class FormationBand:
    name: str
    top_md: float
    bottom_md: float
    lithology: str = ""
    color: str = "#455a64"
    pp_ppg: float = 0.0
    fg_ppg: float = 0.0


LITHO_COLORS = {
    "sandstone": "#c19a6b", "shale": "#5d4037",
    "limestone": "#9e9e9e", "dolomite": "#8d6e63",
    "anhydrite": "#b0bec5", "salt": "#e0e0e0",
    "carbonate": "#757575", "claystone": "#6d4c41",
    "silt": "#a1887f", "schist": "#4e342e",
    "sand": "#d4a574", "marl": "#795548",
    "default": "#546e7a",
}


def _color_for_litho(litho: str) -> str:
    litho_lower = litho.lower()
    for key, color in LITHO_COLORS.items():
        if key in litho_lower:
            return color
    return LITHO_COLORS["default"]


class WellboreSchematic:
    def __init__(self):
        self.sections: List[SchematicSection] = []
        self.formations: List[FormationBand] = []
        self.total_depth_ft: float = 0.0

    def add_casing(self, name, top_md, bottom_md, od_in, id_in,
                     weight_ppf=0.0, grade=""):
        self.sections.append(SchematicSection(
            name=name, kind="casing", top_md=top_md,
            bottom_md=bottom_md, id_in=id_in, od_in=od_in,
            weight_ppf=weight_ppf, grade=grade, color="#90a4ae"))
        self.total_depth_ft = max(self.total_depth_ft, bottom_md)

    def add_liner(self, name, top_md, bottom_md, od_in, id_in,
                    weight_ppf=0.0, grade=""):
        self.sections.append(SchematicSection(
            name=name, kind="liner", top_md=top_md,
            bottom_md=bottom_md, id_in=id_in, od_in=od_in,
            weight_ppf=weight_ppf, grade=grade, color="#b0bec5"))
        self.total_depth_ft = max(self.total_depth_ft, bottom_md)

    def add_open_hole(self, name, top_md, bottom_md, hole_id_in):
        self.sections.append(SchematicSection(
            name=name, kind="openhole", top_md=top_md,
            bottom_md=bottom_md, id_in=hole_id_in, color="#ffd54f"))
        self.total_depth_ft = max(self.total_depth_ft, bottom_md)

    def add_formation(self, name, top_md, bottom_md, lithology="",
                        pp_ppg=0.0, fg_ppg=0.0):
        self.formations.append(FormationBand(
            name=name, top_md=top_md, bottom_md=bottom_md,
            lithology=lithology, color=_color_for_litho(lithology),
            pp_ppg=pp_ppg, fg_ppg=fg_ppg))

    @classmethod
    def from_hole_sections(cls, sections) -> "WellboreSchematic":
        s = cls()
        for sec in sections:
            if sec.casing_id_in and sec.casing_od_in:
                s.add_casing(
                    name=sec.name, top_md=sec.top_md,
                    bottom_md=min(sec.bottom_md,
                                    sec.casing_shoe_md or sec.bottom_md),
                    od_in=sec.casing_od_in, id_in=sec.casing_id_in)
            if sec.casing_shoe_md and sec.casing_shoe_md < sec.bottom_md:
                s.add_open_hole(
                    name=f"{sec.name} OH",
                    top_md=sec.casing_shoe_md,
                    bottom_md=sec.bottom_md,
                    hole_id_in=sec.hole_id_in)
            elif not sec.casing_id_in:
                s.add_open_hole(
                    name=f"{sec.name} OH", top_md=sec.top_md,
                    bottom_md=sec.bottom_md, hole_id_in=sec.hole_id_in)
        return s

    def to_dict(self) -> dict:
        return {
            "total_depth_ft": self.total_depth_ft,
            "sections": [
                {"name": s.name, "kind": s.kind, "top_md": s.top_md,
                 "bottom_md": s.bottom_md, "id_in": s.id_in,
                 "od_in": s.od_in, "color": s.color,
                 "weight_ppf": s.weight_ppf, "grade": s.grade}
                for s in self.sections],
            "formations": [
                {"name": f.name, "top_md": f.top_md,
                 "bottom_md": f.bottom_md, "lithology": f.lithology,
                 "color": f.color, "pp_ppg": f.pp_ppg, "fg_ppg": f.fg_ppg}
                for f in self.formations],
        }

    def kuwait_formations_preload(self) -> None:
        KUWAIT = [
            ("Dammam", 0, 1000, "limestone", 8.65, 12.0),
            ("Rus", 1000, 2500, "anhydrite", 8.65, 12.5),
            ("Radhuma", 2500, 3200, "dolomite", 8.70, 13.0),
            ("Tayarat", 3200, 4200, "shale", 8.70, 13.5),
            ("Shiranish", 4200, 5000, "shale", 8.65, 13.8),
            ("Hartha", 5000, 5800, "limestone", 8.65, 14.2),
            ("Sadi", 5800, 6200, "limestone", 8.65, 14.5),
            ("Tanuma", 6200, 6500, "shale", 8.70, 14.8),
            ("Khasib", 6500, 6800, "limestone", 8.75, 15.0),
            ("Mishrif", 6800, 7200, "limestone", 8.80, 15.3),
            ("Rumaila", 7200, 8000, "limestone", 8.85, 15.5),
            ("Ahmadi", 8000, 8600, "shale", 8.90, 15.8),
            ("Wara", 8600, 9000, "sandstone", 8.95, 16.0),
            ("Mauddud", 9000, 9500, "limestone", 9.00, 16.3),
            ("Burgan", 9500, 10000, "sandstone", 9.05, 16.5),
            ("Shuaiba", 10000, 11000, "limestone", 9.10, 16.8),
            ("Zubair", 11000, 11800, "sandstone", 9.20, 17.2),
            ("Ratawi", 11800, 12600, "limestone", 9.30, 17.5),
            ("Minagish", 12600, 13300, "limestone", 9.40, 17.8),
            ("Makhul", 13300, 14200, "limestone", 9.55, 18.2),
            ("Hith", 14200, 14800, "anhydrite", 9.65, 18.4),
            ("Gotnia", 14800, 15300, "salt", 9.80, 18.7),
            ("Najmah", 15300, 15900, "limestone", 9.90, 19.0),
            ("Sargelu", 15900, 16400, "limestone", 10.05, 19.3),
            ("Dharuma", 16400, 16900, "shale", 10.15, 19.5),
            ("Marrat", 16900, 17500, "limestone", 10.30, 19.8),
        ]
        for name, top, bot, litho, pp, fg in KUWAIT:
            self.add_formation(name, top, bot, litho, pp, fg)
