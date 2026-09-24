"""Simple metrics collector."""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    def __init__(self):
        self._lock = threading.RLock()
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = {}
        self._start_time = time.time()

    def increment(self, name: str, delta: float = 1.0) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + delta

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = []
            self._histograms[name].append(value)
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-1000:]

    def snapshot(self) -> Dict:
        with self._lock:
            hist_stats = {}
            for name, values in self._histograms.items():
                if not values:
                    continue
                sorted_v = sorted(values)
                n = len(sorted_v)
                hist_stats[name] = {
                    "count": n,
                    "min": sorted_v[0],
                    "max": sorted_v[-1],
                    "mean": sum(sorted_v) / n,
                    "p50": sorted_v[n // 2],
                    "p95": sorted_v[int(n * 0.95)] if n > 20 else sorted_v[-1],
                }
            return {
                "uptime_s": round(time.time() - self._start_time, 1),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": hist_stats,
                "timestamp": time.time(),
            }


_metrics: Optional[MetricsCollector] = None
_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        with _lock:
            if _metrics is None:
                _metrics = MetricsCollector()
    return _metrics
