"""Overpull & Stuck Point Analysis."""

import math
from dataclasses import dataclass, field
from typing import List, Optional

from arhpp.mechanics.types import OperationType
from arhpp.mechanics.torque_drag import _pipe_area_in2


@dataclass
class OverpullAnalysis:
    free_hookload_klb: float = 0.0
    current_hookload_klb: float = 0.0
    operation: OperationType = OperationType.PULLING_OUT
    overpull_klb: float = 0.0
    overpull_pct: float = 0.0
    string_yield_margin_klb: float = 0.0
    rig_limit_margin_klb: float = 0.0
    stuck_point_md_ft: Optional[float] = None
    stuck_point_tvd_ft: Optional[float] = None
    confidence: float = 0.0
    status: str = "normal"
    warnings: List[str] = field(default_factory=list)


@dataclass
class StuckPointAnalysis:
    stuck_md_ft: float = 0.0
    stuck_tvd_ft: float = 0.0
    method: str = "stretch"
    confidence: float = 0.0
    stretch_in: float = 0.0
    free_length_ft: float = 0.0
    warnings: List[str] = field(default_factory=list)


class StuckPointEstimator:
    def estimate_from_stretch(self, delta_length_in: float,
                                 overpull_klb: float,
                                 pipe_od_in: float,
                                 pipe_id_in: float,
                                 total_md_ft: float,
                                 youngs_psi: float = 30e6
                                 ) -> StuckPointAnalysis:
        result = StuckPointAnalysis(method="stretch")
        if overpull_klb <= 0 or pipe_od_in <= 0:
            result.warnings.append("Invalid inputs")
            return result
        area_in2 = _pipe_area_in2(pipe_od_in, pipe_id_in)
        if area_in2 <= 0:
            return result
        F_lb = overpull_klb * 1000.0
        L_free_in = delta_length_in * youngs_psi * area_in2 / F_lb
        L_free_ft = L_free_in / 12.0
        result.free_length_ft = L_free_ft
        result.stuck_md_ft = max(0.0, total_md_ft - L_free_ft)
        result.stretch_in = delta_length_in
        result.confidence = min(1.0, delta_length_in / 20.0)
        return result

    def estimate_from_torque(self, delta_torque_ftlb: float,
                                pipe_od_in: float,
                                pipe_id_in: float,
                                total_md_ft: float,
                                shear_modulus_psi: float = 11.5e6
                                ) -> StuckPointAnalysis:
        result = StuckPointAnalysis(method="torque")
        if delta_torque_ftlb <= 0 or pipe_od_in <= 0:
            return result
        J_in4 = math.pi / 32.0 * (pipe_od_in ** 4 - pipe_id_in ** 4)
        r_in = pipe_od_in / 2.0
        T_lb_in = delta_torque_ftlb * 12.0
        if T_lb_in <= 0:
            return result
        L_free_ft = (delta_torque_ftlb * 12.0 * shear_modulus_psi
                       * J_in4 / (T_lb_in * r_in)) / 12.0
        result.free_length_ft = L_free_ft
        result.stuck_md_ft = max(0.0, total_md_ft - L_free_ft)
        result.confidence = 0.6
        return result


def compute_overpull(free_hookload_klb: float,
                       current_hookload_klb: float,
                       string_yield_klb: float = 550.0,
                       rig_limit_klb: float = 750.0,
                       operation: OperationType = OperationType.PULLING_OUT
                       ) -> OverpullAnalysis:
    result = OverpullAnalysis(
        free_hookload_klb=free_hookload_klb,
        current_hookload_klb=current_hookload_klb,
        operation=operation)
    delta = current_hookload_klb - free_hookload_klb
    result.overpull_klb = delta
    if free_hookload_klb > 0:
        result.overpull_pct = 100.0 * delta / free_hookload_klb
    result.string_yield_margin_klb = string_yield_klb - current_hookload_klb
    result.rig_limit_margin_klb = rig_limit_klb - current_hookload_klb

    if current_hookload_klb >= string_yield_klb * 0.95:
        result.status = "critical"
        result.warnings.append(
            f"Hookload at {current_hookload_klb:.0f} klb - near yield!")
    elif current_hookload_klb >= rig_limit_klb * 0.90:
        result.status = "high"
        result.warnings.append(
            f"Hookload approaching rig limit ({rig_limit_klb:.0f} klb)")
    elif delta > 50.0:
        result.status = "elevated"
        result.warnings.append(
            f"Overpull {delta:.0f} klb detected - possible stuck pipe")
    else:
        result.status = "normal"
    return result
