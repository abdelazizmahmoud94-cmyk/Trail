"""Control modes: MANUAL, COMPUTER (PID), AP (Adaptive Pressure).

CRITICAL: Choke position is INVERSE to SBP.
  Closing choke (lower %) -> SBP rises
  Opening choke (higher %) -> SBP drops
So we use error = measurement - setpoint (inverted).
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from arhpp.plc.choke import ChokeModel
from arhpp.plc.types import ControlMode


@dataclass
class PIDController:
    kp: float = 0.05
    ki: float = 0.002
    kd: float = 0.10
    deadband_psi: float = 5.0
    min_output: float = 0.0
    max_output: float = 100.0
    anti_windup: bool = True
    _integral: float = 0.0
    _last_error: float = 0.0
    _last_ts: float = field(default_factory=time.time)
    _last_output: float = 0.0

    def reset(self) -> None:
        self._integral = 0.0
        self._last_error = 0.0
        self._last_ts = time.time()
        self._last_output = 0.0

    def update(self, setpoint: float, measurement: float,
                 dt_s: Optional[float] = None) -> float:
        now = time.time()
        if dt_s is None:
            dt_s = max(1e-3, now - self._last_ts)
        self._last_ts = now

        # Inverted error (choke is inverse plant)
        error = measurement - setpoint

        if abs(error) < self.deadband_psi:
            return self._last_output

        p_term = self.kp * error
        self._integral += error * dt_s
        i_term = self.ki * self._integral
        d_error = (error - self._last_error) / dt_s if dt_s > 0 else 0.0
        d_term = self.kd * d_error
        self._last_error = error

        output = self._last_output + p_term + i_term + d_term

        if output > self.max_output:
            output = self.max_output
            if self.anti_windup:
                self._integral -= error * dt_s
        elif output < self.min_output:
            output = self.min_output
            if self.anti_windup:
                self._integral -= error * dt_s

        self._last_output = output
        return output


@dataclass
class APController:
    bhp_target_psi: float = 9500.0
    gain: float = 0.015
    deadband_psi: float = 15.0
    min_output: float = 0.0
    max_output: float = 100.0
    _last_bhp: float = 0.0
    _last_output: float = 0.0
    _last_ts: float = field(default_factory=time.time)

    def update(self, bhp_predicted: float, sbp_measured: float) -> float:
        now = time.time()
        self._last_ts = now
        error = bhp_predicted - self.bhp_target_psi
        if abs(error) < self.deadband_psi:
            return self._last_output
        delta_choke = self.gain * error
        output = self._last_output + delta_choke
        output = max(self.min_output, min(self.max_output, output))
        self._last_output = output
        self._last_bhp = bhp_predicted
        return output

    def reset(self) -> None:
        self._last_output = 0.0
        self._last_bhp = 0.0
        self._last_ts = time.time()


class ChokeModeManager:
    def __init__(self, choke: ChokeModel):
        self.choke = choke
        self.mode: ControlMode = ControlMode.MANUAL
        self.setpoint_psi: float = 0.0
        self.pid = PIDController()
        self.ap = APController()

    def set_mode(self, mode: ControlMode,
                   setpoint_psi: float = 0.0) -> None:
        if mode == self.mode and abs(setpoint_psi - self.setpoint_psi) < 1e-3:
            return
        if mode != self.mode:
            self.pid.reset()
            self.ap.reset()
        self.mode = mode
        self.setpoint_psi = setpoint_psi
        if mode == ControlMode.AP:
            self.ap.bhp_target_psi = setpoint_psi

    def update(self, dt_s: float, sbp_measured: float,
                 bhp_predicted: float = 0.0,
                 manual_position_pct: Optional[float] = None) -> float:
        if self.mode == ControlMode.MANUAL:
            if manual_position_pct is not None:
                self.choke.set_command(manual_position_pct,
                                         mode=ControlMode.MANUAL,
                                         source="operator")
            return self.choke.commanded_pct
        elif self.mode == ControlMode.COMPUTER:
            out = self.pid.update(self.setpoint_psi, sbp_measured, dt_s)
            self.choke.set_command(out, mode=ControlMode.COMPUTER,
                                     source="computer")
            return out
        elif self.mode == ControlMode.AP:
            out = self.ap.update(bhp_predicted, sbp_measured)
            self.choke.set_command(out, mode=ControlMode.AP, source="ap")
            return out
        elif self.mode == ControlMode.SAFE:
            self.choke.set_command(0.0, mode=ControlMode.SAFE,
                                     source="safe_mode")
            return 0.0
        return self.choke.commanded_pct

    def info(self) -> dict:
        return {
            "choke_id": self.choke.choke_id,
            "mode": self.mode.value,
            "setpoint_psi": round(self.setpoint_psi, 2),
            "commanded_pct": round(self.choke.commanded_pct, 3),
            "actual_pct": round(self.choke.actual_pct, 3),
        }
