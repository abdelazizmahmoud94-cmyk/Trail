"""Graph Builder — time-series + depth-series."""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from arhpp.viz.channel_manager import get_channel_manager


@dataclass
class GraphSpec:
    graph_id: str
    title: str = ""
    x_axis: str = "time"
    x_unit: str = "s"
    duration_s: float = 240.0
    channels: List[str] = field(default_factory=list)
    units: str = "imperial"
    show_grid: bool = True
    show_legend: bool = True
    auto_scale: bool = True
    y_min: Optional[float] = None
    y_max: Optional[float] = None


class CircularBuffer:
    def __init__(self, maxlen: int = 10000):
        self.maxlen = maxlen
        self._xs: List[float] = []
        self._ys: List[float] = []
        self._ts: List[float] = []

    def push(self, x: float, y: float, ts: float = 0.0) -> None:
        self._xs.append(x)
        self._ys.append(y)
        self._ts.append(ts)
        if len(self._xs) > self.maxlen:
            self._xs = self._xs[-self.maxlen:]
            self._ys = self._ys[-self.maxlen:]
            self._ts = self._ts[-self.maxlen:]

    def filter_range(self, x_min: float, x_max: float
                       ) -> Tuple[List[float], List[float]]:
        out_x, out_y = [], []
        for x, y in zip(self._xs, self._ys):
            if x_min <= x <= x_max:
                out_x.append(x)
                out_y.append(y)
        return out_x, out_y

    def stats(self, x_min=None, x_max=None) -> dict:
        if x_min is not None and x_max is not None:
            _, ys = self.filter_range(x_min, x_max)
        else:
            ys = self._ys
        if not ys:
            return {"min": 0, "max": 0, "mean": 0, "last": 0, "n": 0}
        return {
            "min": min(ys), "max": max(ys),
            "mean": sum(ys) / len(ys), "last": ys[-1], "n": len(ys)}

    def __len__(self):
        return len(self._xs)


class GraphBuilder:
    def __init__(self, max_points_per_channel: int = 20000):
        self.max_points = max_points_per_channel
        self.buffers: Dict[str, CircularBuffer] = {}
        self.start_time: float = 0.0

    def push(self, channel_id: str, value: float,
              time_s: float, ts: float = 0.0) -> None:
        if channel_id not in self.buffers:
            self.buffers[channel_id] = CircularBuffer(self.max_points)
        self.buffers[channel_id].push(time_s, value, ts)

    def push_snapshot(self, snapshot: Dict, time_s: float,
                       ts: float = 0.0) -> None:
        for channel_id, value in snapshot.items():
            if isinstance(value, (int, float)):
                self.push(channel_id, float(value), time_s, ts)

    def build(self, spec: GraphSpec) -> dict:
        cm = get_channel_manager()
        if spec.x_axis == "time":
            x_min = max(0.0, self._now() - spec.duration_s)
            x_max = self._now()
        else:
            x_min = 0.0
            x_max = 1e6

        traces = []
        for ch_id in spec.channels:
            ch = cm.get(ch_id)
            if not ch:
                continue
            buf = self.buffers.get(ch_id)
            if not buf or len(buf) == 0:
                traces.append({"channel_id": ch_id, "name": ch.label,
                                "x": [], "y": [], "color": ch.color,
                                "unit": ch.unit})
                continue
            xs, ys = buf.filter_range(x_min, x_max)
            if spec.units == "metric" and ch.metric_unit:
                ys = [ch.convert_to_metric(y) for y in ys]
                unit = ch.metric_unit
            else:
                unit = ch.unit
            traces.append({
                "channel_id": ch_id, "name": ch.label,
                "x": xs, "y": ys, "color": ch.color, "unit": unit,
                "stats": buf.stats(x_min, x_max)})

        if spec.auto_scale:
            y_min, y_max = self._compute_y_range(traces)
        else:
            y_min = spec.y_min or 0.0
            y_max = spec.y_max or 100.0

        return {
            "spec": {
                "graph_id": spec.graph_id,
                "title": spec.title or spec.graph_id,
                "x_axis": spec.x_axis, "x_unit": spec.x_unit,
                "duration_s": spec.duration_s, "units": spec.units,
                "show_grid": spec.show_grid,
                "show_legend": spec.show_legend},
            "range": {"x_min": x_min, "x_max": x_max,
                        "y_min": y_min, "y_max": y_max},
            "traces": traces,
        }

    def _now(self) -> float:
        if self.start_time == 0.0:
            return 0.0
        import time
        return time.time() - self.start_time

    @staticmethod
    def _compute_y_range(traces: List[dict]):
        y_min, y_max = float("inf"), float("-inf")
        for t in traces:
            for y in t["y"]:
                y_min = min(y_min, y)
                y_max = max(y_max, y)
        if y_min == float("inf"):
            return 0.0, 1.0
        span = max(y_max - y_min, 1e-3)
        return y_min - 0.1 * span, y_max + 0.1 * span

    @staticmethod
    def main_graph_specs() -> List[GraphSpec]:
        return [
            GraphSpec("flow", "Flow",
                       channels=["q_in_gpm", "q_out_gpm", "q_effective_gpm"]),
            GraphSpec("density", "Density",
                       channels=["mw_in_ppg", "mw_out_ppg", "ecd_ppg"]),
            GraphSpec("sbp", "Surface Back Pressure",
                       channels=["sbp_psi"]),
            GraphSpec("spp", "Standpipe Pressure",
                       channels=["spp_psi"]),
            GraphSpec("bhp", "Bottom Hole Pressure",
                       channels=["bhp_psi", "pwd_bhp_psi"]),
            GraphSpec("chokes", "Chokes",
                       channels=["choke_a_pct", "choke_b_pct"]),
        ]

    @staticmethod
    def custom_graph_spec(graph_id: str, channels: List[str],
                            duration_s: float = 86400.0,
                            sample_interval_s: float = 5.0) -> GraphSpec:
        return GraphSpec(graph_id=graph_id,
                           title=f"Custom: {', '.join(channels[:3])}",
                           channels=channels, duration_s=duration_s)
