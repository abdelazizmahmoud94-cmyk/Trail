"""Kick Auto-Control state machine."""

import time
from dataclasses import dataclass, field
from typing import Optional, List, Callable

from arhpp.plc.types import KickState
from arhpp.events.kick import KickInputs, compute_kick, KickResult


@dataclass
class KickAutoConfig:
    flow_imbalance_gpm: float = 30.0
    pit_gain_bbl: float = 5.0
    gas_units_threshold: float = 100.0
    min_confidence: float = 0.7
    target_sbp_psi: float = 450.0
    sbp_ramp_rate_psi_sec: float = 5.0
    max_sbp_psi: float = 1500.0
    detect_window_s: float = 5.0
    pressuring_timeout_s: float = 30.0
    stabilizing_timeout_s: float = 120.0
    max_choke_rate_pct_sec: float = 10.0
    min_choke_pct: float = 5.0


@dataclass
class KickAutoEvent:
    timestamp: float
    state_from: KickState
    state_to: KickState
    note: str = ""


class KickAutoController:
    def __init__(self, config: Optional[KickAutoConfig] = None):
        self.config = config or KickAutoConfig()
        self.state: KickState = KickState.DISARMED
        self.state_since: float = time.time()
        self.events: List[KickAutoEvent] = []
        self._kick_result: Optional[KickResult] = None
        self._target_sbp: float = 0.0
        self._sbp_at_arm: float = 0.0
        self._pit_gain_at_arm: float = 0.0
        self._on_state_change: Optional[Callable] = None
        self._on_kick_detected: Optional[Callable] = None

    def register_hooks(self, on_state_change=None, on_kick_detected=None):
        self._on_state_change = on_state_change
        self._on_kick_detected = on_kick_detected

    def _transition(self, new_state: KickState, note: str = "") -> None:
        if new_state == self.state:
            return
        old = self.state
        self.state = new_state
        self.state_since = time.time()
        self.events.append(KickAutoEvent(
            timestamp=self.state_since,
            state_from=old, state_to=new_state, note=note))
        if self._on_state_change:
            try:
                self._on_state_change(old, new_state)
            except Exception:
                pass

    def arm(self) -> None:
        if self.state == KickState.DISARMED:
            self._transition(KickState.ARMED, "operator arm")

    def disarm(self) -> None:
        self._transition(KickState.DISARMED, "operator disarm")

    def update(self, dt_s: float, q_in_gpm: float, q_out_gpm: float,
                 pit_gain_bbl: float, sbp_measured_psi: float,
                 bg_gas: float = 0.0, cg_gas: float = 0.0,
                 tg_gas: float = 0.0, tvd_ft: float = 15000.0,
                 mw_ppg: float = 12.0,
                 annular_fp_psi: float = 300.0) -> dict:
        now = time.time()

        if self.state == KickState.DISARMED:
            return {"action": "NONE", "note": "disarmed"}

        if self.state == KickState.ARMED:
            kick_result = compute_kick(KickInputs(
                q_in_gpm=q_in_gpm, q_out_gpm=q_out_gpm,
                pit_gain_bbl=pit_gain_bbl,
                background_gas_units=bg_gas,
                connection_gas_units=cg_gas,
                trip_gas_units=tg_gas,
                pumps_off=False, tvd_ft=tvd_ft, mw_ppg=mw_ppg,
                annular_fp_psi=annular_fp_psi))

            if kick_result.probability >= self.config.min_confidence:
                self._kick_result = kick_result
                self._sbp_at_arm = sbp_measured_psi
                self._pit_gain_at_arm = pit_gain_bbl
                self._target_sbp = min(
                    self.config.max_sbp_psi,
                    sbp_measured_psi + 200.0)
                self._transition(
                    KickState.DETECTED,
                    f"kick prob={kick_result.probability:.2f}")
                if self._on_kick_detected:
                    try:
                        self._on_kick_detected(kick_result)
                    except Exception:
                        pass
                return {"action": "NONE",
                         "note": f"kick detected prob={kick_result.probability:.2f}",
                         "kick_result": kick_result}
            return {"action": "NONE", "note": "armed, monitoring"}

        if self.state == KickState.DETECTED:
            if now - self.state_since > 2.0:
                self._transition(KickState.PRESSURING,
                                   f"target SBP = {self._target_sbp:.0f}")
            return {"action": "NONE", "note": "confirming detection",
                     "target_sbp": self._target_sbp}

        if self.state == KickState.PRESSURING:
            if sbp_measured_psi >= self._target_sbp - 5.0:
                self._transition(KickState.STABILIZING, "target SBP reached")
                return {"action": "HOLD_SBP",
                         "target_sbp_psi": self._target_sbp}
            if now - self.state_since > self.config.pressuring_timeout_s:
                self._transition(KickState.ESCALATED, "pressuring timeout")
                return {"action": "STOP_DRILL",
                         "note": "escalated: pressuring timeout"}
            return {"action": "RAMP_SBP",
                     "target_sbp_psi": self._target_sbp,
                     "ramp_rate_psi_sec": self.config.sbp_ramp_rate_psi_sec}

        if self.state == KickState.STABILIZING:
            if now - self.state_since > self.config.stabilizing_timeout_s:
                if abs(pit_gain_bbl - self._pit_gain_at_arm) < 1.0:
                    self._transition(KickState.SUCCESS, "pit stable 120s")
                    return {"action": "HOLD_SBP",
                             "target_sbp_psi": self._target_sbp}
                else:
                    self._transition(KickState.ESCALATED,
                                       "pit gain continuing")
                    return {"action": "STOP_DRILL",
                             "note": "escalated: pit still gaining"}
            if pit_gain_bbl - self._pit_gain_at_arm > 10.0:
                self._transition(KickState.ESCALATED,
                                   f"pit +{pit_gain_bbl - self._pit_gain_at_arm:.1f}")
                return {"action": "STOP_DRILL",
                         "note": "escalated: pit fast rise"}
            return {"action": "HOLD_SBP",
                     "target_sbp_psi": self._target_sbp}

        if self.state in (KickState.SUCCESS, KickState.ESCALATED):
            self._transition(KickState.RECOVERING, "prepare for handover")
            return {"action": "HOLD_SBP",
                     "target_sbp_psi": self._target_sbp}

        if self.state == KickState.RECOVERING:
            if now - self.state_since > 30.0:
                self._transition(KickState.ARMED, "handed to operator")
            return {"action": "HOLD_SBP",
                     "target_sbp_psi": self._target_sbp}

        return {"action": "NONE"}

    def info(self) -> dict:
        return {
            "state": self.state.value,
            "duration_s": round(time.time() - self.state_since, 1),
            "target_sbp": round(self._target_sbp, 1),
            "n_events": len(self.events),
            "recent_events": [
                {"ts": e.timestamp, "from": e.state_from.value,
                 "to": e.state_to.value, "note": e.note}
                for e in self.events[-10:]
            ],
        }
