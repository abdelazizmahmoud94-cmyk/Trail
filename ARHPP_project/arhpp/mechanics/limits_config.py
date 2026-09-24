"""Limits Configuration — parameters for mechanical events."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class LimitDirection(str, Enum):
    HIGH = "high"
    LOW = "low"
    BOTH = "both"


@dataclass
class ParameterLimit:
    param_name: str
    display_name: str
    unit: str
    normal_min: float = 0.0
    normal_max: float = 0.0
    warning_pct: float = 0.10
    critical_pct: float = 0.25
    direction: LimitDirection = LimitDirection.HIGH
    event_type_name: str = "custom"

    @property
    def warning_max(self) -> float:
        return self.normal_max * (1.0 + self.warning_pct)

    @property
    def critical_max(self) -> float:
        return self.normal_max * (1.0 + self.critical_pct)

    @property
    def warning_min(self) -> float:
        if self.direction == LimitDirection.HIGH:
            return 0.0
        return self.normal_min * (1.0 - self.warning_pct)

    @property
    def critical_min(self) -> float:
        if self.direction == LimitDirection.HIGH:
            return 0.0
        return self.normal_min * (1.0 - self.critical_pct)

    def classify(self, value: float) -> str:
        if self.direction in (LimitDirection.HIGH, LimitDirection.BOTH):
            if value >= self.critical_max:
                return "critical"
            if value >= self.warning_max:
                return "warning"
        if self.direction in (LimitDirection.LOW, LimitDirection.BOTH):
            if value <= self.critical_min:
                return "critical"
            if value <= self.warning_min:
                return "warning"
        return "normal"

    def threshold_for(self, zone: str) -> float:
        if zone == "critical":
            if self.direction == LimitDirection.LOW:
                return self.critical_min
            return self.critical_max
        if zone == "warning":
            if self.direction == LimitDirection.LOW:
                return self.warning_min
            return self.warning_max
        return 0.0

    def to_dict(self) -> dict:
        return {
            "param_name": self.param_name,
            "display_name": self.display_name,
            "unit": self.unit,
            "normal_min": self.normal_min,
            "normal_max": self.normal_max,
            "warning_max": self.warning_max,
            "critical_max": self.critical_max,
            "warning_min": self.warning_min,
            "critical_min": self.critical_min,
            "direction": self.direction.value,
            "warning_pct": self.warning_pct,
            "critical_pct": self.critical_pct,
            "event_type_name": self.event_type_name,
        }


DEFAULT_LIMITS: Dict[str, ParameterLimit] = {
    "hookload_klb": ParameterLimit(
        "hookload_klb", "Hookload", "klb", 0, 550, 0.05, 0.15,
        LimitDirection.HIGH, "overpull"),
    "surface_torque_ftlb": ParameterLimit(
        "surface_torque_ftlb", "Surface Torque", "ft-lb",
        0, 22000, 0.10, 0.25, LimitDirection.HIGH, "high_torque"),
    "overpull_klb": ParameterLimit(
        "overpull_klb", "Overpull", "klb", 0, 80, 0.25, 0.75,
        LimitDirection.HIGH, "overpull"),
    "drag_klb": ParameterLimit(
        "drag_klb", "Drag", "klb", 0, 60, 0.20, 0.50,
        LimitDirection.HIGH, "high_drag"),
    "wob_klb": ParameterLimit(
        "wob_klb", "WOB", "klb", 0, 40, 0.20, 0.50,
        LimitDirection.HIGH, "high_wob"),
    "rpm": ParameterLimit(
        "rpm", "RPM", "rpm", 0, 180, 0.10, 0.25,
        LimitDirection.HIGH, "high_rpm"),
    "vibration_g": ParameterLimit(
        "vibration_g", "Vibration", "g", 0, 3.0, 0.33, 1.00,
        LimitDirection.HIGH, "vibration"),
    "spp_psi": ParameterLimit(
        "spp_psi", "SPP", "psi", 0, 5000, 0.10, 0.25,
        LimitDirection.HIGH, "high_spp"),
    "bhp_psi": ParameterLimit(
        "bhp_psi", "BHP", "psi", 0, 15000, 0.05, 0.15,
        LimitDirection.HIGH, "high_bhp"),
    "ecd_ppg": ParameterLimit(
        "ecd_ppg", "ECD", "ppg", 8.0, 15.0, 0.05, 0.10,
        LimitDirection.BOTH, "high_ecd"),
    "sbp_psi": ParameterLimit(
        "sbp_psi", "SBP", "psi", 0, 1500, 0.10, 0.25,
        LimitDirection.HIGH, "high_sbp"),
    "compression_klb": ParameterLimit(
        "compression_klb", "Axial Compression", "klb",
        0, 30, 0.20, 0.50, LimitDirection.HIGH, "buckling"),
}


class LimitsRegistry:
    def __init__(self, initial=None):
        self._limits: Dict[str, ParameterLimit] = dict(
            initial or DEFAULT_LIMITS)

    def get(self, param_name: str) -> ParameterLimit:
        return self._limits.get(param_name)

    def set(self, limit: ParameterLimit) -> None:
        self._limits[limit.param_name] = limit

    def update(self, param_name: str,
                 normal_max=None, normal_min=None,
                 warning_pct=None, critical_pct=None):
        limit = self._limits.get(param_name)
        if limit is None:
            return None
        if normal_max is not None:
            limit.normal_max = normal_max
        if normal_min is not None:
            limit.normal_min = normal_min
        if warning_pct is not None:
            limit.warning_pct = warning_pct
        if critical_pct is not None:
            limit.critical_pct = critical_pct
        return limit

    def all_limits(self) -> List[ParameterLimit]:
        return list(self._limits.values())

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self._limits.items()}

    def reset_to_defaults(self) -> None:
        self._limits = dict(DEFAULT_LIMITS)


_registry: Optional[LimitsRegistry] = None


def get_limits_registry() -> LimitsRegistry:
    global _registry
    if _registry is None:
        _registry = LimitsRegistry()
    return _registry
