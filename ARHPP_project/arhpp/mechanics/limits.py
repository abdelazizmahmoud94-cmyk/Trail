"""Rig Limits Checker."""

from dataclasses import dataclass, field
from typing import List, Optional

from arhpp.mechanics.types import RigLimits


@dataclass
class LimitCheck:
    name: str
    current: float
    limit: float
    unit: str = ""
    pct: float = 0.0
    status: str = "ok"
    margin: float = 0.0
    message: str = ""


@dataclass
class LimitsReport:
    checks: List[LimitCheck] = field(default_factory=list)
    overall_status: str = "ok"
    warnings: List[str] = field(default_factory=list)


class LimitsChecker:
    def __init__(self, limits: Optional[RigLimits] = None):
        self.limits = limits or RigLimits()

    def check_all(self, hookload_klb: float = 0.0,
                    surface_torque_ftlb: float = 0.0,
                    make_up_torque_ftlb: float = 0.0,
                    max_stress_psi: float = 0.0,
                    yield_stress_psi: float = 80000.0) -> LimitsReport:
        report = LimitsReport()
        report.checks.append(self._check(
            "Hookload", hookload_klb,
            self.limits.rig_hoisting_limit_klb, "klb"))
        report.checks.append(self._check(
            "Surface Torque", surface_torque_ftlb,
            self.limits.max_rig_torque_ftlb, "ft-lb"))
        if make_up_torque_ftlb > 0:
            report.checks.append(self._check(
                "Make-up Torque", make_up_torque_ftlb,
                self.limits.max_makeup_torque_ftlb, "ft-lb"))
        if max_stress_psi > 0:
            report.checks.append(self._check(
                "Von Mises Stress", max_stress_psi, yield_stress_psi, "psi"))

        worst = "ok"
        for c in report.checks:
            if c.status == "critical":
                worst = "critical"
                break
            if c.status == "danger" and worst != "critical":
                worst = "danger"
            elif c.status == "warn" and worst == "ok":
                worst = "warn"
        report.overall_status = worst
        report.warnings = [c.message for c in report.checks if c.message]
        return report

    @staticmethod
    def _check(name: str, current: float, limit: float,
                 unit: str = "") -> LimitCheck:
        pct = 100.0 * current / limit if limit > 0 else 0.0
        margin = limit - current
        if pct >= 100.0:
            status = "critical"
            msg = f"{name} EXCEEDED limit! {current:.1f}/{limit:.1f} {unit}"
        elif pct >= 90.0:
            status = "danger"
            msg = f"{name} at {pct:.1f}% of limit"
        elif pct >= 75.0:
            status = "warn"
            msg = f"{name} at {pct:.1f}% of limit"
        else:
            status = "ok"
            msg = ""
        return LimitCheck(name=name, current=current, limit=limit,
                            unit=unit, pct=pct, status=status,
                            margin=margin, message=msg)
