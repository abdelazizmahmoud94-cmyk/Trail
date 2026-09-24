"""Real-Time Loop — reads sensors and emits ARHPP outputs at each tick."""

import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from arhpp.sensors.base import SensorAdapter, SensorReading
from arhpp.sensors.buffer import ReadingBuffer


@dataclass
class RealtimeConfig:
    survey: list = field(default_factory=list)
    hole_sections: list = field(default_factory=list)
    bha: list = field(default_factory=list)
    bit_nozzles: list = field(default_factory=list)
    bit_diameter_in: float = 8.5
    cd: float = 0.95
    eccentricity: float = 0.5
    string_segments_raw: list = field(default_factory=list)
    annulus_segments_raw: list = field(default_factory=list)
    buffer_size: int = 3600
    tick_seconds: float = 1.0
    on_tick: Optional[Callable] = None


class RealtimeLoop:
    def __init__(self, adapter: SensorAdapter, cfg: RealtimeConfig):
        self.adapter = adapter
        self.cfg = cfg
        self.buffer = ReadingBuffer(maxlen=cfg.buffer_size)
        self.tick = 0
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self, max_ticks: Optional[int] = None) -> None:
        with self.adapter:
            while not self._stop:
                reading = self.adapter.read()
                if reading is not None:
                    self.buffer.push(reading)
                    out = self.process(reading)
                    if self.cfg.on_tick:
                        self.cfg.on_tick(out)
                self.tick += 1
                if max_ticks is not None and self.tick >= max_ticks:
                    break
                time.sleep(self.cfg.tick_seconds)

    def process(self, latest: SensorReading) -> dict:
        """Simple pipeline — returns reading dict + buffer stats."""
        return {
            "tick": self.tick,
            "timestamp": latest.timestamp,
            "reading": latest,
            "buffer": self.buffer,
        }
