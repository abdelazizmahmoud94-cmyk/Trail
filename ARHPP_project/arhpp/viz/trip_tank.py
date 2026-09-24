"""Virtual Trip Tank."""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class TripTankState:
    time_s: float = 0.0
    bit_md_ft: float = 0.0
    trip_speed_fps: float = 0.0
    direction: str = "static"
    tank_capacity_bbl: float = 100.0
    tank_id_in: float = 24.0
    current_volume_bbl: float = 0.0
    current_level_ft: float = 0.0
    expected_volume_change_bbl: float = 0.0
    actual_volume_change_bbl: float = 0.0
    deviation_bbl: float = 0.0
    deviation_pct: float = 0.0
    classification: str = "normal"
    cumulative_gain_bbl: float = 0.0
    cumulative_loss_bbl: float = 0.0


class VirtualTripTank:
    def __init__(self, tank_capacity_bbl: float = 100.0,
                 tank_id_in: float = 24.0,
                 pipe_displacement_bblft: float = 0.0459,
                 hole_capacity_bblft: float = 0.0459):
        self.tank_capacity_bbl = tank_capacity_bbl
        self.tank_id_in = tank_id_in
        self.pipe_disp_bblft = pipe_displacement_bblft
        self.hole_cap_bblft = hole_capacity_bblft
        self.start_time = time.time()
        self.initial_volume_bbl = tank_capacity_bbl * 0.5
        self.current_volume_bbl = self.initial_volume_bbl
        self.prev_md: Optional[float] = None
        self.cumulative_gain_bbl = 0.0
        self.cumulative_loss_bbl = 0.0

    def update(self, bit_md_ft: float, trip_speed_fps: float,
                 measured_tank_bbl: Optional[float] = None
                 ) -> TripTankState:
        state = TripTankState(
            time_s=time.time() - self.start_time,
            bit_md_ft=bit_md_ft, trip_speed_fps=trip_speed_fps)
        if abs(trip_speed_fps) < 1e-3:
            state.direction = "static"
        elif trip_speed_fps > 0:
            state.direction = "in"
        else:
            state.direction = "out"

        if self.prev_md is not None:
            delta_md = bit_md_ft - self.prev_md
            expected_delta_bbl = -delta_md * self.pipe_disp_bblft
            state.expected_volume_change_bbl = expected_delta_bbl
            self.current_volume_bbl += expected_delta_bbl
        self.prev_md = bit_md_ft

        if measured_tank_bbl is not None:
            state.actual_volume_change_bbl = (
                measured_tank_bbl - self.initial_volume_bbl)
            deviation = measured_tank_bbl - self.current_volume_bbl
        else:
            state.actual_volume_change_bbl = (
                self.current_volume_bbl - self.initial_volume_bbl)
            deviation = 0.0

        state.current_volume_bbl = self.current_volume_bbl
        state.current_level_ft = self._volume_to_level(
            self.current_volume_bbl)
        state.deviation_bbl = deviation
        if self.current_volume_bbl > 0:
            state.deviation_pct = (100.0 * deviation
                                     / self.tank_capacity_bbl)
        abs_pct = abs(state.deviation_pct)
        if abs_pct < 1.0:
            state.classification = "normal"
        elif abs_pct < 3.0:
            state.classification = "minor"
        elif abs_pct < 8.0:
            state.classification = "moderate"
        else:
            state.classification = "severe"

        if deviation > 0:
            self.cumulative_gain_bbl = max(self.cumulative_gain_bbl,
                                             deviation)
        else:
            self.cumulative_loss_bbl = max(self.cumulative_loss_bbl,
                                             -deviation)
        state.cumulative_gain_bbl = self.cumulative_gain_bbl
        state.cumulative_loss_bbl = self.cumulative_loss_bbl
        return state

    def _volume_to_level(self, volume_bbl: float) -> float:
        if self.tank_id_in <= 0:
            return 0.0
        volume_in3 = volume_bbl * 9702.0
        id_in = self.tank_id_in
        height_in = 4.0 * volume_in3 / (3.14159 * id_in ** 2)
        return height_in / 12.0

    def reset(self) -> None:
        self.current_volume_bbl = self.initial_volume_bbl
        self.prev_md = None
        self.cumulative_gain_bbl = 0.0
        self.cumulative_loss_bbl = 0.0
        self.start_time = time.time()

    def to_dict(self, state: TripTankState) -> dict:
        return {
            "time_s": round(state.time_s, 1),
            "bit_md_ft": round(state.bit_md_ft, 2),
            "trip_speed_fps": round(state.trip_speed_fps, 2),
            "direction": state.direction,
            "tank_capacity_bbl": self.tank_capacity_bbl,
            "current_volume_bbl": round(state.current_volume_bbl, 2),
            "current_level_ft": round(state.current_level_ft, 2),
            "deviation_bbl": round(state.deviation_bbl, 3),
            "deviation_pct": round(state.deviation_pct, 2),
            "classification": state.classification,
            "cumulative_gain_bbl": round(state.cumulative_gain_bbl, 2),
            "cumulative_loss_bbl": round(state.cumulative_loss_bbl, 2),
        }
