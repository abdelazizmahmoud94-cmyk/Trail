"""Trajectory Engine — 2D + 3D trajectory."""

import math
from dataclasses import dataclass, field
from typing import List


@dataclass
class Trajectory3D:
    md: List[float] = field(default_factory=list)
    north: List[float] = field(default_factory=list)
    east: List[float] = field(default_factory=list)
    tvd: List[float] = field(default_factory=list)
    inc: List[float] = field(default_factory=list)
    azi: List[float] = field(default_factory=list)
    dls: List[float] = field(default_factory=list)

    def summary(self) -> dict:
        if not self.md:
            return {}
        return {
            "n_points": len(self.md),
            "md_start": self.md[0], "md_end": self.md[-1],
            "tvd_start": self.tvd[0], "tvd_end": self.tvd[-1],
            "north_end": self.north[-1], "east_end": self.east[-1],
            "displacement_ft": math.sqrt(
                self.north[-1] ** 2 + self.east[-1] ** 2),
            "max_dls": max(self.dls) if self.dls else 0.0,
            "max_inc": max(self.inc) if self.inc else 0.0,
        }


@dataclass
class Trajectory2D:
    section_name: str = "Custom"
    azimuth_deg: float = 0.0
    md: List[float] = field(default_factory=list)
    vertical_section: List[float] = field(default_factory=list)
    tvd: List[float] = field(default_factory=list)


class TrajectoryEngine:
    def compute_3d(self, survey) -> Trajectory3D:
        traj = Trajectory3D()
        for p in survey:
            traj.md.append(p.md)
            traj.north.append(p.north)
            traj.east.append(p.east)
            traj.tvd.append(p.tvd)
            traj.inc.append(p.inc)
            traj.azi.append(p.azi)
            traj.dls.append(p.dls)
        return traj

    def compute_2d_section(self, survey, azimuth_deg: float,
                             name: str = "Custom") -> Trajectory2D:
        azi_rad = math.radians(azimuth_deg)
        sec = Trajectory2D(section_name=name, azimuth_deg=azimuth_deg)
        for p in survey:
            sec.md.append(p.md)
            sec.tvd.append(p.tvd)
            vs = (p.north * math.cos(azi_rad)
                    + p.east * math.sin(azi_rad))
            sec.vertical_section.append(vs)
        return sec

    def compute_full_package(self, survey) -> dict:
        traj3d = self.compute_3d(survey)
        target_azi = survey[-1].azi if survey else 0.0
        section = self.compute_2d_section(survey, target_azi,
                                            name="Target Azimuth")
        return {
            "trajectory_3d": {
                "md": traj3d.md, "north": traj3d.north,
                "east": traj3d.east, "tvd": traj3d.tvd,
                "inc": traj3d.inc, "azi": traj3d.azi, "dls": traj3d.dls},
            "sections": {
                "plan_view": {"x": traj3d.east, "y": traj3d.north},
                "north_tvd": {"x": traj3d.north, "y": traj3d.tvd},
                "east_tvd": {"x": traj3d.east, "y": traj3d.tvd},
                "vertical_section": {
                    "x": section.vertical_section,
                    "y": section.tvd,
                    "azimuth": target_azi}},
            "summary": traj3d.summary(),
        }
