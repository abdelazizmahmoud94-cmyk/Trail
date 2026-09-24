"""Watchdog + Safe Mode logic."""

import time
from dataclasses import dataclass, field
from typing import Callable, List

from arhpp.plc.types import SafeModeReason


@dataclass
class Watchdog:
    timeout_s: float = 0.5
    _last_kick: float = field(default_factory=time.time)
    _timeout_count: int = 0

    def kick(self) -> None:
        self._last_kick = time.time()

    def is_ok(self) -> bool:
        return (time.time() - self._last_kick) < self.timeout_s

    def check_timeout(self) -> bool:
        if not self.is_ok():
            self._timeout_count += 1
            return True
        return False

    def age_s(self) -> float:
        return time.time() - self._last_kick

    @property
    def timeout_count(self) -> int:
        return self._timeout_count


@dataclass
class SafeModeEvent:
    timestamp: float
    reason: SafeModeReason
    note: str = ""


class SafeModeManager:
    def __init__(self):
        self.active: bool = False
        self.reason: SafeModeReason = SafeModeReason.NONE
        self.activated_at: float = 0.0
        self.events: List[SafeModeEvent] = []
        self._callbacks: List[Callable] = []

    def register_callback(self, cb: Callable) -> None:
        self._callbacks.append(cb)

    def activate(self, reason: SafeModeReason, note: str = "") -> None:
        if self.active:
            return
        self.active = True
        self.reason = reason
        self.activated_at = time.time()
        self.events.append(SafeModeEvent(
            timestamp=self.activated_at, reason=reason, note=note))
        for cb in self._callbacks:
            try:
                cb(reason)
            except Exception:
                pass

    def clear(self, note: str = "manual clear") -> None:
        if not self.active:
            return
        self.events.append(SafeModeEvent(
            timestamp=time.time(),
            reason=SafeModeReason.MANUAL_TRIGGER,
            note=f"CLEAR: {note}"))
        self.active = False
        self.reason = SafeModeReason.NONE

    def duration_s(self) -> float:
        if not self.active:
            return 0.0
        return time.time() - self.activated_at

    def info(self) -> dict:
        return {
            "active": self.active,
            "reason": self.reason.value,
            "duration_s": round(self.duration_s(), 1),
            "n_events": len(self.events),
            "recent_events": [
                {"ts": e.timestamp, "reason": e.reason.value, "note": e.note}
                for e in self.events[-5:]
            ],
        }
