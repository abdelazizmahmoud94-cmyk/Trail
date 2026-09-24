"""Trip Simulator — generate TripState at each timestep."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class TripState:
    time_s: float = 0.0
    bit_md: float = 0.0
    trip_speed_fps: float = 0.0
    direction: str = "static"
    closed_end: bool = False

    def is_moving(self) -> bool:
        return abs(self.trip_speed_fps) > 1e-6


def simulate_trip(start_md: float, end_md: float,
                    speed_fps: float, direction: str,
                    closed_end: bool = False,
                    dt_s: float = 30.0) -> List[TripState]:
    """Uniform-speed trip simulator."""
    if speed_fps <= 0:
        raise ValueError("speed_fps must be > 0")

    direction = direction.lower()
    if direction == "in":
        sign = +1.0
    elif direction == "out":
        sign = -1.0
    else:
        raise ValueError("direction must be 'in' or 'out'")

    vp = sign * speed_fps
    states: List[TripState] = []
    t = 0.0
    md = start_md

    for _ in range(20000):
        states.append(TripState(
            time_s=t, bit_md=md, trip_speed_fps=vp,
            direction=direction, closed_end=closed_end,
        ))
        step_ft = speed_fps * dt_s
        if direction == "in":
            if md >= end_md - 1e-6:
                break
            md = min(end_md, md + step_ft)
        else:
            if md <= end_md + 1e-6:
                break
            md = max(end_md, md - step_ft)
        t += dt_s

    return states


def recommended_max_speed(current_state, bha_sections, hole_sections,
                            annulus_col, survey, target_dp_psi,
                            probe_speeds_fps=(1, 2, 3, 5, 7, 10, 15)):
    """Find max safe trip speed whose surge/swab dP stays under target."""
    from arhpp.hydraulics.surge_swab import compute_surge_swab
    sign = 1.0 if current_state.direction == "in" else -1.0
    best = 0.0
    for sp in probe_speeds_fps:
        r = compute_surge_swab(
            bit_md=current_state.bit_md,
            vp_fps=sign * sp,
            closed_end=current_state.closed_end,
            bha_sections=bha_sections,
            hole_sections=hole_sections,
            annulus_col=annulus_col,
            survey=survey,
        )
        if abs(r.total_dp_psi) <= target_dp_psi:
            best = sp
        else:
            break
    return best
