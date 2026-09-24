"""Shared runtime state for the API."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import threading


@dataclass
class RuntimeState:
    latest: Optional[Dict[str, Any]] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    history_max: int = 3600
    started_at: datetime = field(default_factory=datetime.utcnow)
    tick_count: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def push(self, snapshot: Dict[str, Any]) -> None:
        with self.lock:
            self.latest = snapshot
            self.history.append(snapshot)
            if len(self.history) > self.history_max:
                self.history = self.history[-self.history_max:]
            self.tick_count += 1

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "latest": self.latest,
                "tick_count": self.tick_count,
                "started_at": self.started_at.isoformat(),
                "history_len": len(self.history),
            }

    def get_history(self, n: int = 300) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.history[-n:])


STATE = RuntimeState()
