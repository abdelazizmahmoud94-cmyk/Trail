"""Choke model — valve + response dynamics + flow."""

import math
import time
from dataclasses import dataclass, field
from typing import Optional

from arhpp.plc.types import ChokeState, ControlMode, CHOKE_CV_CURVE


def _interp_cv(position_pct: float) -> float:
    p = max(0.0, min(100.0, position_pct))
    pts = CHOKE_CV_CURVE
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        if p <= x1:
            if x1 == x0:
                return y1
            f = (p - x0) / (x1 - x0)
            return y0 + f * (y1 - y0)
    return pts[-1][1]


def compute_choke_flow(position_pct: float, upstream_psi: float,
                         downstream_psi: float, cv_max: float = 1.0,
                         choke_id: str = "CHOKE-A") -> float:
    """
    Flow [gpm] = Cv_max * Cv_factor(Position) * sqrt(dP / SG)
    """
    if position_pct <= 0.01:
        return 0.0
    dp = max(0.0, upstream_psi - downstream_psi)
    if dp <= 0:
        return 0.0
    cv = cv_max * _interp_cv(position_pct)
    q_gpm = cv * math.sqrt(dp) * 100.0
    return max(0.0, q_gpm)


@dataclass
class ChokeModel:
    choke_id: str = "CHOKE-A"
    commanded_pct: float = 0.0
    actual_pct: float = 0.0
    rate_limit_pct_sec: float = 5.0
    time_constant_s: float = 0.15
    deadband_pct: float = 0.10
    hysteresis_pct: float = 0.50
    cv_max: float = 3.5
    trim_type: str = "S-curve"
    last_update_s: float = field(default_factory=time.time)
    last_rate_pct_sec: float = 0.0
    total_travel: float = 0.0
    cycles: int = 0
    fail_safe_position_pct: float = 0.0
    fail_active: bool = False

    def set_command(self, position_pct: float,
                     mode: ControlMode = ControlMode.MANUAL,
                     source: str = "operator") -> None:
        self.commanded_pct = max(0.0, min(100.0, position_pct))

    def update(self, dt_s: float, upstream_psi: float = 0.0,
                 downstream_psi: float = 0.0) -> dict:
        self.last_update_s = time.time()
        self.cycles += 1

        if self.fail_active:
            target = self.fail_safe_position_pct
        else:
            diff = self.commanded_pct - self.actual_pct
            if abs(diff) < self.deadband_pct:
                target = self.actual_pct
            else:
                target = self.commanded_pct

        delta = target - self.actual_pct
        max_change = self.rate_limit_pct_sec * dt_s
        if abs(delta) > max_change:
            delta = max_change * (1 if delta > 0 else -1)

        if self.time_constant_s > 0:
            tc_factor = 1.0 - math.exp(-dt_s / self.time_constant_s)
            delta *= tc_factor * 3.0
            delta = max(-max_change, min(max_change, delta))

        old_pos = self.actual_pct
        self.actual_pct = max(0.0, min(100.0, self.actual_pct + delta))
        actual_change = self.actual_pct - old_pos
        self.total_travel += abs(actual_change)
        self.last_rate_pct_sec = actual_change / dt_s if dt_s > 0 else 0.0

        if abs(actual_change) < 1e-4:
            if abs(self.commanded_pct - self.actual_pct) < self.deadband_pct:
                state = ChokeState.HOLDING
            else:
                state = ChokeState.IDLE
        elif actual_change > 0:
            state = ChokeState.OPENING
        else:
            state = ChokeState.CLOSING

        q_gpm = compute_choke_flow(
            self.actual_pct, upstream_psi, downstream_psi,
            cv_max=self.cv_max, choke_id=self.choke_id)

        return {
            "choke_id": self.choke_id,
            "commanded_pct": self.commanded_pct,
            "actual_pct": self.actual_pct,
            "rate_pct_sec": self.last_rate_pct_sec,
            "is_moving": (state in (ChokeState.OPENING, ChokeState.CLOSING)),
            "state": state.value,
            "upstream_pressure_psi": upstream_psi,
            "downstream_pressure_psi": downstream_psi,
            "flow_gpm": q_gpm,
        }

    def trigger_fail_safe(self, position_pct: float = 0.0) -> None:
        self.fail_safe_position_pct = position_pct
        self.fail_active = True

    def clear_fail_safe(self) -> None:
        self.fail_active = False

    def info(self) -> dict:
        return {
            "choke_id": self.choke_id,
            "commanded_pct": round(self.commanded_pct, 3),
            "actual_pct": round(self.actual_pct, 3),
            "rate_pct_sec": round(self.last_rate_pct_sec, 3),
            "total_travel": round(self.total_travel, 2),
            "cycles": self.cycles,
            "fail_active": self.fail_active,
            "cv_max": self.cv_max,
            "trim": self.trim_type,
        }
