"""Friction Factor Sensitivity Study."""

import math
from dataclasses import dataclass, field
from typing import List, Optional

from arhpp.mechanics.types import TDInputs, OperationType
from arhpp.mechanics.torque_drag import TorqueDragEngine


@dataclass
class FFPoint:
    friction_factor: float = 0.0
    hookload_klb: float = 0.0
    surface_torque_ftlb: float = 0.0
    max_stress_psi: float = 0.0


@dataclass
class FFSensitivityResult:
    operation: OperationType
    ff_values: List[float] = field(default_factory=list)
    hookload_curve: List[FFPoint] = field(default_factory=list)
    torque_curve: List[FFPoint] = field(default_factory=list)
    actual_ff: Optional[float] = None
    actual_hookload_klb: Optional[float] = None
    actual_torque_ftlb: Optional[float] = None


class FrictionFactorStudy:
    def __init__(self, engine: Optional[TorqueDragEngine] = None):
        self.engine = engine or TorqueDragEngine()

    def run_sensitivity(self, survey, bha_sections,
                          inputs: TDInputs,
                          hole_id_in: float = 8.5,
                          ff_values: Optional[List[float]] = None
                          ) -> FFSensitivityResult:
        if ff_values is None:
            ff_values = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60]
        result = FFSensitivityResult(
            operation=inputs.operation, ff_values=ff_values)

        for ff in ff_values:
            local = TDInputs(
                operation=inputs.operation,
                friction_factor=ff,
                wob_klb=inputs.wob_klb,
                rpm=inputs.rpm,
                torque_at_bit_ftlb=inputs.torque_at_bit_ftlb,
                block_weight_klb=inputs.block_weight_klb,
                mud_weight_ppg=inputs.mud_weight_ppg,
                tvd_ft=inputs.tvd_ft)
            td = self.engine.compute(survey, bha_sections, local, hole_id_in)
            point = FFPoint(
                friction_factor=ff,
                hookload_klb=td.hookload_klb,
                surface_torque_ftlb=td.surface_torque_ftlb,
                max_stress_psi=td.max_von_mises_psi)
            result.hookload_curve.append(point)
            result.torque_curve.append(point)
        return result

    def find_actual_ff(self, result: FFSensitivityResult,
                         actual_hookload_klb: float) -> Optional[float]:
        curve = sorted(result.hookload_curve,
                        key=lambda p: p.friction_factor)
        if len(curve) < 2:
            return None
        for i in range(1, len(curve)):
            a, b = curve[i - 1], curve[i]
            h_a, h_b = a.hookload_klb, b.hookload_klb
            if (h_a <= actual_hookload_klb <= h_b) or \
               (h_b <= actual_hookload_klb <= h_a):
                if abs(h_b - h_a) < 1e-6:
                    return a.friction_factor
                f = (actual_hookload_klb - h_a) / (h_b - h_a)
                return a.friction_factor + f * (
                    b.friction_factor - a.friction_factor)
        return None
