"""Time-series ring buffer for sensor readings."""

from collections import deque
from typing import Optional, List

from arhpp.sensors.base import SensorReading


class ReadingBuffer:
    def __init__(self, maxlen: int = 3600):
        self.data: deque = deque(maxlen=maxlen)

    def push(self, r: SensorReading) -> None:
        self.data.append(r)

    def latest(self) -> Optional[SensorReading]:
        return self.data[-1] if self.data else None

    def window(self, n: int) -> List[SensorReading]:
        return list(self.data)[-n:] if n > 0 else []

    def trend(self, field_name: str, n: int = 30) -> float:
        w = self.window(n)
        if len(w) < 2:
            return 0.0
        vals = [getattr(r, field_name, 0.0) for r in w]
        k = len(vals)
        x_mean = (k - 1) / 2.0
        y_mean = sum(vals) / k
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(vals))
        den = sum((i - x_mean) ** 2 for i in range(k))
        return num / den if den > 0 else 0.0

    def mean(self, field_name: str, n: int = 30) -> float:
        w = self.window(n)
        if not w:
            return 0.0
        return sum(getattr(r, field_name, 0.0) for r in w) / len(w)

    def std(self, field_name: str, n: int = 30) -> float:
        w = self.window(n)
        if len(w) < 2:
            return 0.0
        vals = [getattr(r, field_name, 0.0) for r in w]
        m = sum(vals) / len(vals)
        var = sum((v - m) ** 2 for v in vals) / (len(vals) - 1)
        return var ** 0.5
