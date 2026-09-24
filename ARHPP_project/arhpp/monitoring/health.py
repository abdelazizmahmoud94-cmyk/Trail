"""Health checks."""

import time
from dataclasses import dataclass
from typing import Dict, Callable


@dataclass
class HealthCheck:
    name: str
    status: str = "UNKNOWN"
    message: str = ""
    latency_ms: float = 0.0
    checked_at: float = 0.0


class HealthChecker:
    def __init__(self):
        self._checks: Dict[str, Callable] = {}

    def register(self, name: str, fn: Callable) -> None:
        self._checks[name] = fn

    def run_all(self) -> Dict:
        results = []
        overall = "OK"
        for name, fn in self._checks.items():
            t0 = time.time()
            try:
                status, message = fn()
            except Exception as e:
                status, message = "FAIL", str(e)
            latency = (time.time() - t0) * 1000
            results.append(HealthCheck(
                name=name, status=status, message=message,
                latency_ms=round(latency, 2), checked_at=time.time()))
            if status == "FAIL":
                overall = "FAIL"
            elif status == "WARN" and overall == "OK":
                overall = "WARN"
        return {
            "status": overall,
            "checks": [
                {"name": c.name, "status": c.status,
                 "message": c.message, "latency_ms": c.latency_ms}
                for c in results],
            "checked_at": time.time(),
        }


def default_health_checker() -> HealthChecker:
    hc = HealthChecker()

    def _disk():
        import shutil
        total, used, free = shutil.disk_usage("/")
        pct = 100.0 * used / total
        if pct > 90:
            return "FAIL", f"Disk {pct:.1f}% full"
        if pct > 75:
            return "WARN", f"Disk {pct:.1f}% full"
        return "OK", f"Disk {pct:.1f}% used"

    def _memory():
        try:
            import psutil
            m = psutil.virtual_memory()
            if m.percent > 90:
                return "FAIL", f"Memory {m.percent}%"
            if m.percent > 75:
                return "WARN", f"Memory {m.percent}%"
            return "OK", f"Memory {m.percent}%"
        except ImportError:
            return "OK", "psutil not installed"

    def _python():
        import sys
        if sys.version_info < (3, 10):
            return "FAIL", f"Python {sys.version}"
        return "OK", f"Python {sys.version.split()[0]}"

    hc.register("disk", _disk)
    hc.register("memory", _memory)
    hc.register("python", _python)
    return hc
