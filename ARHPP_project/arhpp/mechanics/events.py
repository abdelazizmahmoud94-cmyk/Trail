"""Mechanical Event Tracker — value-based lifecycle.

Logic:
  value crosses limit      -> Event created (ACTIVE)
  value returns to normal  -> Event auto-cleared (CLEARED) instantly
  value crosses again      -> Event RECURRED

No counters. No clean passes. Only actual values.
"""

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Callable
from threading import RLock
from collections import defaultdict

from arhpp.mechanics.limits_config import (
    ParameterLimit, LimitsRegistry, get_limits_registry,
)


class EventType(str, Enum):
    HIGH_TORQUE = "high_torque"
    HIGH_DRAG = "high_drag"
    OVERPULL = "overpull"
    STUCK_PIPE = "stuck_pipe"
    VIBRATION = "vibration"
    BUCKLING = "buckling"
    HIGH_WOB = "high_wob"
    HIGH_RPM = "high_rpm"
    HIGH_SPP = "high_spp"
    HIGH_BHP = "high_bhp"
    HIGH_ECD = "high_ecd"
    LOW_ECD = "low_ecd"
    HIGH_SBP = "high_sbp"
    LOW_ROP = "low_rop"
    KICK = "kick"
    LOSS = "loss"
    WASHOUT = "washout"
    BALLING = "balling"
    PACKOFF = "packoff"
    NOZZLE_PLUG = "nozzle_plug"
    CUSTOM = "custom"


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class EventState(str, Enum):
    ACTIVE = "active"
    CLEARED = "cleared"
    RECURRED = "recurred"
    FALSE_POSITIVE = "false_positive"


@dataclass
class MechanicalEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: EventType = EventType.CUSTOM
    severity: EventSeverity = EventSeverity.WARNING
    state: EventState = EventState.ACTIVE
    md_ft: float = 0.0
    tvd_ft: float = 0.0
    depth_window_ft: float = 30.0
    detected_at: float = field(default_factory=time.time)
    cleared_at: Optional[float] = None
    last_seen_at: float = field(default_factory=time.time)
    param_name: str = ""
    unit: str = ""
    value: float = 0.0
    peak_value: float = 0.0
    threshold: float = 0.0
    normal_max: float = 0.0
    exceedance_pct: float = 0.0
    operation: str = ""
    message: str = ""
    metadata: Dict = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)

    def is_terminal(self) -> bool:
        return self.state in (EventState.CLEARED,
                                EventState.FALSE_POSITIVE)

    def is_open(self) -> bool:
        return not self.is_terminal()

    def add_history(self, kind: str, note: str = "",
                     value: float = 0.0) -> None:
        self.history.append({
            "timestamp": time.time(),
            "kind": kind,
            "note": note,
            "value": value,
            "state": self.state.value,
        })

    def duration_s(self) -> float:
        end = self.cleared_at or time.time()
        return end - self.detected_at

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        d["severity"] = self.severity.value
        d["state"] = self.state.value
        d["is_open"] = self.is_open()
        d["duration_s"] = round(self.duration_s(), 1)
        return d


@dataclass
class EventTrackerConfig:
    default_depth_window_ft: float = 30.0
    min_event_duration_s: float = 0.0
    bucket_size_ft: float = 100.0
    max_events: int = 5000


class MechanicalEventTracker:
    def __init__(self, config: Optional[EventTrackerConfig] = None,
                 registry: Optional[LimitsRegistry] = None,
                 callbacks: Optional[List[Callable]] = None):
        self.config = config or EventTrackerConfig()
        self.registry = registry or get_limits_registry()
        self._lock = RLock()
        self._events: Dict[str, MechanicalEvent] = {}
        self._by_bucket: Dict[int, List[str]] = defaultdict(list)
        self._active_by_param: Dict[str, str] = {}
        self._callbacks: List[Callable] = callbacks or []

    def update_value(self, param_name: str, value: float,
                       md_ft: float, tvd_ft: float = 0.0,
                       operation: str = "") -> Optional[MechanicalEvent]:
        with self._lock:
            limit = self.registry.get(param_name)
            if limit is None:
                return None
            zone = limit.classify(value)
            existing_id = self._active_by_param.get(param_name)
            existing = self._events.get(existing_id) if existing_id else None

            if zone == "normal":
                if existing and existing.is_open():
                    existing.state = EventState.CLEARED
                    existing.cleared_at = time.time()
                    existing.value = value
                    existing.add_history(
                        "CLEARED",
                        f"{limit.display_name} returned to normal "
                        f"({value:.1f} {limit.unit})",
                        value=value)
                    del self._active_by_param[param_name]
                    self._fire_callbacks("cleared", existing)
                    return existing
                return None

            severity = self._severity_for_zone(zone)
            threshold = limit.threshold_for(zone)

            if existing is None:
                old_ev = self._find_cleared_for_param(param_name, md_ft)
                if old_ev:
                    old_ev.state = EventState.RECURRED
                    old_ev.cleared_at = None
                    old_ev.last_seen_at = time.time()
                    old_ev.value = value
                    old_ev.severity = severity
                    old_ev.add_history(
                        "RECURRED",
                        f"{limit.display_name} exceeded again: "
                        f"{value:.1f} {limit.unit}",
                        value=value)
                    self._active_by_param[param_name] = old_ev.event_id
                    self._fire_callbacks("recurred", old_ev)
                    return old_ev

                ev = self._create_event(
                    limit=limit, value=value, md_ft=md_ft,
                    tvd_ft=tvd_ft, zone=zone, severity=severity,
                    threshold=threshold, operation=operation)
                self._active_by_param[param_name] = ev.event_id
                self._fire_callbacks("created", ev)
                return ev

            existing.value = value
            existing.last_seen_at = time.time()
            if value > existing.peak_value:
                existing.peak_value = value
            if self._severity_rank(severity) > self._severity_rank(existing.severity):
                existing.severity = severity
                existing.add_history("ESCALATED",
                    f"Severity -> {severity.value} ({value:.1f} {limit.unit})",
                    value=value)
            else:
                existing.add_history("VALUE_UPDATE",
                    f"{value:.1f} {limit.unit} (zone={zone})", value=value)
            return existing

    def update_snapshot(self, values: Dict[str, float], md_ft: float,
                          tvd_ft: float = 0.0,
                          operation: str = "") -> List[MechanicalEvent]:
        touched = []
        for param_name, value in values.items():
            ev = self.update_value(param_name, value, md_ft,
                                     tvd_ft, operation)
            if ev is not None:
                touched.append(ev)
        return touched

    def clear_manually(self, event_id: str,
                        operator: str = "operator",
                        note: str = "") -> bool:
        with self._lock:
            ev = self._events.get(event_id)
            if not ev:
                return False
            ev.state = EventState.CLEARED
            ev.cleared_at = time.time()
            ev.add_history("MANUAL_CLEAR",
                            f"Cleared by {operator}. {note}".strip())
            if ev.param_name in self._active_by_param:
                del self._active_by_param[ev.param_name]
            self._fire_callbacks("cleared", ev)
            return True

    def mark_false_positive(self, event_id: str,
                              operator: str = "operator",
                              note: str = "") -> bool:
        with self._lock:
            ev = self._events.get(event_id)
            if not ev:
                return False
            ev.state = EventState.FALSE_POSITIVE
            ev.cleared_at = time.time()
            ev.add_history("FALSE_POSITIVE",
                            f"Marked by {operator}. {note}".strip())
            if ev.param_name in self._active_by_param:
                del self._active_by_param[ev.param_name]
            self._fire_callbacks("false_positive", ev)
            return True

    def get_open_events(self) -> List[MechanicalEvent]:
        with self._lock:
            return [e for e in self._events.values() if e.is_open()]

    def get_active_event(self, param_name: str) -> Optional[MechanicalEvent]:
        with self._lock:
            eid = self._active_by_param.get(param_name)
            return self._events.get(eid) if eid else None

    def get_all_events(self) -> List[MechanicalEvent]:
        with self._lock:
            return list(self._events.values())

    def get_event(self, event_id: str) -> Optional[MechanicalEvent]:
        with self._lock:
            return self._events.get(event_id)

    def get_events_by_md_range(self, md_min: float, md_max: float,
                                 include_terminal: bool = True
                                 ) -> List[MechanicalEvent]:
        with self._lock:
            out = [e for e in self._events.values()
                    if md_min <= e.md_ft <= md_max
                    and (include_terminal or not e.is_terminal())]
            return sorted(out, key=lambda e: e.md_ft)

    def get_events_by_type(self, ev_type: EventType) -> List[MechanicalEvent]:
        with self._lock:
            return [e for e in self._events.values()
                    if e.event_type == ev_type]

    def get_feedback_log(self, limit: int = 200,
                           state_filter: Optional[List[EventState]] = None,
                           type_filter: Optional[List[EventType]] = None,
                           md_min: Optional[float] = None,
                           md_max: Optional[float] = None
                           ) -> List[Dict]:
        with self._lock:
            entries = []
            for ev in self._events.values():
                if state_filter and ev.state not in state_filter:
                    continue
                if type_filter and ev.event_type not in type_filter:
                    continue
                if md_min is not None and ev.md_ft < md_min:
                    continue
                if md_max is not None and ev.md_ft > md_max:
                    continue
                for h in ev.history:
                    entries.append({
                        "event_id": ev.event_id,
                        "event_type": ev.event_type.value,
                        "severity": ev.severity.value,
                        "md_ft": ev.md_ft,
                        "tvd_ft": ev.tvd_ft,
                        "param_name": ev.param_name,
                        "unit": ev.unit,
                        "timestamp": h["timestamp"],
                        "kind": h["kind"],
                        "note": h["note"],
                        "value": h.get("value", 0.0),
                        "state": ev.state.value,
                        "is_terminal": ev.is_terminal(),
                        "operation": ev.operation,
                    })
            entries.sort(key=lambda e: e["timestamp"], reverse=True)
            return entries[:limit]

    def get_stats(self) -> Dict:
        with self._lock:
            by_state = defaultdict(int)
            by_type = defaultdict(int)
            by_severity = defaultdict(int)
            for ev in self._events.values():
                by_state[ev.state.value] += 1
                by_type[ev.event_type.value] += 1
                by_severity[ev.severity.value] += 1
            return {
                "total_events": len(self._events),
                "open_events": len(self.get_open_events()),
                "active_by_param": dict(self._active_by_param),
                "by_state": dict(by_state),
                "by_type": dict(by_type),
                "by_severity": dict(by_severity),
            }

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._by_bucket.clear()
            self._active_by_param.clear()

    def _create_event(self, limit: ParameterLimit, value: float,
                        md_ft: float, tvd_ft: float, zone: str,
                        severity: EventSeverity, threshold: float,
                        operation: str) -> MechanicalEvent:
        exceedance_pct = 0.0
        if limit.normal_max > 0:
            exceedance_pct = 100.0 * (value - limit.normal_max) / limit.normal_max
        ev_type = self._event_type_from_name(limit.event_type_name)
        ev = MechanicalEvent(
            event_type=ev_type, severity=severity,
            state=EventState.ACTIVE, md_ft=md_ft, tvd_ft=tvd_ft or md_ft,
            depth_window_ft=self.config.default_depth_window_ft,
            param_name=limit.param_name, unit=limit.unit,
            value=value, peak_value=value, threshold=threshold,
            normal_max=limit.normal_max, exceedance_pct=exceedance_pct,
            operation=operation,
            message=(f"{limit.display_name} = {value:.1f} {limit.unit} "
                      f"(zone: {zone}, limit: {limit.normal_max:.1f})"),
            metadata={"zone": zone, "limit_name": limit.display_name})
        ev.add_history("DETECTED",
            f"{limit.display_name} = {value:.1f} {limit.unit} "
            f"crossed {zone} limit ({threshold:.1f} {limit.unit})",
            value=value)
        self._events[ev.event_id] = ev
        bucket = int(ev.md_ft // self.config.bucket_size_ft)
        self._by_bucket[bucket].append(ev.event_id)
        return ev

    def _find_cleared_for_param(self, param_name: str,
                                  md_ft: float
                                  ) -> Optional[MechanicalEvent]:
        window = self.config.default_depth_window_ft
        bucket = int(md_ft // self.config.bucket_size_ft)
        candidates = []
        for b in (bucket - 1, bucket, bucket + 1):
            for eid in self._by_bucket.get(b, []):
                ev = self._events.get(eid)
                if ev is None:
                    continue
                if ev.param_name != param_name:
                    continue
                if abs(ev.md_ft - md_ft) > window:
                    continue
                if ev.state == EventState.CLEARED:
                    candidates.append(ev)
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.cleared_at or 0)

    @staticmethod
    def _severity_for_zone(zone: str) -> EventSeverity:
        if zone == "critical":
            return EventSeverity.CRITICAL
        if zone == "warning":
            return EventSeverity.HIGH
        return EventSeverity.WARNING

    @staticmethod
    def _severity_rank(sev: EventSeverity) -> int:
        return {EventSeverity.INFO: 0, EventSeverity.WARNING: 1,
                 EventSeverity.HIGH: 2, EventSeverity.CRITICAL: 3}.get(sev, 0)

    @staticmethod
    def _event_type_from_name(name: str) -> EventType:
        try:
            return EventType(name)
        except ValueError:
            return EventType.CUSTOM

    def _fire_callbacks(self, kind: str, ev: MechanicalEvent) -> None:
        for cb in self._callbacks:
            try:
                cb(kind, ev)
            except Exception:
                pass


_tracker: Optional[MechanicalEventTracker] = None


def get_event_tracker() -> MechanicalEventTracker:
    global _tracker
    if _tracker is None:
        _tracker = MechanicalEventTracker()
    return _tracker
