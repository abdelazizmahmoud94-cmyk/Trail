"""Jar Placement Analysis — corrected Impact Energy formula."""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class JarType(str, Enum):
    HYDRAULIC = "hydraulic"
    MECHANICAL = "mechanical"
    HYDRAULIC_MECHANICAL = "hyd_mech"
    SPRING = "spring"


@dataclass
class JarPlacement:
    jar_type: JarType = JarType.HYDRAULIC
    jar_md_ft: float = 0.0
    jar_tvd_ft: float = 0.0
    hammer_length_in: float = 6.0
    anvil_length_in: float = 6.0
    up_force_klb: float = 0.0
    down_force_klb: float = 0.0
    overpull_klb: float = 0.0
    max_force_at_jar_klb: float = 0.0
    max_force_at_stuck_point_klb: float = 0.0
    impact_energy_ftlb: float = 0.0
    impulse_klb_s: float = 0.0
    impact_efficiency: float = 0.0
    available_impulse: float = 0.0
    warnings: List[str] = field(default_factory=list)
    status: str = "ok"


def compute_jar_impact(overpull_klb: float,
                         hammer_length_in: float,
                         jar_type: JarType = JarType.HYDRAULIC,
                         string_stiffness_klb_in: float = 50.0,
                         bit_weight_klb: float = 20.0) -> dict:
    out = {}
    if overpull_klb <= 0:
        return {"error": "overpull must be > 0"}

    dynamic_factor = 1.5 if jar_type == JarType.HYDRAULIC else 1.3
    max_force_jar = overpull_klb * dynamic_factor
    out["max_force_at_jar_klb"] = max_force_jar
    out["max_force_at_stuck_point_klb"] = max_force_jar * 0.85

    # Impact energy: E = 0.5 * F^2 / k  [lb-in] -> [ft-lb]
    if string_stiffness_klb_in > 0:
        F_lb = overpull_klb * 1000.0
        k_lb_in = string_stiffness_klb_in * 1000.0
        E_lbin = 0.5 * (F_lb ** 2) / k_lb_in
        E_ftlb = E_lbin / 12.0
    else:
        E_ftlb = 0.0

    # Bound by hammer stroke
    if hammer_length_in > 0:
        E_max_stroke = overpull_klb * 1000.0 * hammer_length_in / 12.0
        E_ftlb = min(E_ftlb, E_max_stroke)
    out["impact_energy_ftlb"] = E_ftlb

    out["impulse_klb_s"] = max_force_jar * 0.05
    efficiency_map = {
        JarType.HYDRAULIC: 0.85,
        JarType.HYDRAULIC_MECHANICAL: 0.80,
        JarType.MECHANICAL: 0.70,
        JarType.SPRING: 0.60,
    }
    out["impact_efficiency"] = efficiency_map.get(jar_type, 0.70)
    out["available_impulse"] = out["impulse_klb_s"] * out["impact_efficiency"]

    warnings = []
    if overpull_klb > 400:
        warnings.append(f"Very high overpull: {overpull_klb:.0f} klb")
    if out["max_force_at_jar_klb"] > 550:
        warnings.append(
            f"Jar force {out['max_force_at_jar_klb']:.0f} klb "
            f"may exceed string yield")
    if string_stiffness_klb_in <= 0:
        warnings.append("String stiffness unknown - energy not calculated")
    out["warnings"] = warnings
    out["status"] = "warning" if warnings else "ok"
    return out


def recommend_jar_depth(stuck_md_ft: float,
                          target_up_force_klb: float = 300.0,
                          string_stiffness_klb_in: float = 50.0,
                          friction_factor: float = 0.25) -> dict:
    if stuck_md_ft <= 0:
        return {"recommended_md_ft": 0.0, "recommendations": []}
    offsets = [90, 180, 270, 360, 450]
    recommendations = []
    for offset in offsets:
        jar_md = stuck_md_ft - offset
        if jar_md > 0:
            effective_force = target_up_force_klb * (
                1.0 - friction_factor * offset / 1000.0)
            recommendations.append({
                "jar_md_ft": round(jar_md, 1),
                "offset_from_stuck_ft": offset,
                "estimated_force_klb": round(effective_force, 1),
            })
    return {
        "stuck_md_ft": stuck_md_ft,
        "recommendations": recommendations,
        "best_md_ft": recommendations[0]["jar_md_ft"] if recommendations else 0.0,
        "notes": [
            "Jar should be 1-5 stands above stuck point",
            "Closer - more force, Less - less efficient",
            "Consider jarring up vs down based on stuck direction",
        ],
    }
