"""Gas Models — BG/CG/TG/POG as PP indicators."""

from dataclasses import dataclass
from typing import List

import numpy as np

from arhpp.core.constants import (
    GAS_BG_BASELINE_MAX, GAS_CG_SIGNIFICANT,
    GAS_TG_SIGNIFICANT, GAS_POG_SIGNIFICANT,
    GIF_LOW_GAS_THRESHOLD, GIF_MOD_GAS_THRESHOLD,
    GIF_LOW_PPG, GIF_MOD_PPG, GIF_HIGH_PPG,
)
from arhpp.calibration.context import get_param


@dataclass
class GasReading:
    md_ft: float = 0.0
    tvd_ft: float = 0.0
    total_gas_units: float = 0.0
    background_gas_units: float = 0.0
    connection_gas_units: float = 0.0
    trip_gas_units: float = 0.0
    pump_off_gas_units: float = 0.0
    time_min: float = 0.0
    connection_made: bool = False
    pumps_off: bool = False


@dataclass
class GasIndicator:
    md_ft: float = 0.0
    tvd_ft: float = 0.0
    bg_score: float = 0.0
    cg_score: float = 0.0
    tg_score: float = 0.0
    pog_score: float = 0.0
    combined_score: float = 0.0
    is_anomaly: bool = False


def _score(v: float, base: float, thr: float) -> float:
    if v <= base:
        return 0.0
    return min(1.0, (v - base) / max(thr, 1e-6))


def compute_gas_indicators(readings: List[GasReading]) -> List[GasIndicator]:
    """Score each gas reading — thresholds from context."""
    if not readings:
        return []

    bg_baseline_max = get_param("gas_bg_baseline_max",
                                  default=GAS_BG_BASELINE_MAX)
    cg_thr = get_param("gas_cg_significant",
                        default=GAS_CG_SIGNIFICANT)
    tg_thr = get_param("gas_tg_significant",
                        default=GAS_TG_SIGNIFICANT)
    pog_thr = get_param("gas_pog_significant",
                         default=GAS_POG_SIGNIFICANT)

    bgs = [r.background_gas_units for r in readings
            if r.background_gas_units > 0]
    base_bg = float(np.median(bgs)) if bgs else bg_baseline_max * 0.5

    out: List[GasIndicator] = []
    for r in readings:
        gi = GasIndicator(md_ft=r.md_ft, tvd_ft=r.tvd_ft)
        gi.bg_score = _score(r.background_gas_units, base_bg,
                              bg_baseline_max)
        if r.connection_made:
            gi.cg_score = _score(r.connection_gas_units, 0.0, cg_thr)
        if r.pumps_off:
            gi.pog_score = _score(r.pump_off_gas_units, 0.0, pog_thr)
        if r.trip_gas_units > 0:
            gi.tg_score = _score(r.trip_gas_units, 0.0, tg_thr)

        gi.combined_score = min(1.0, (
            0.20 * gi.bg_score
            + 0.35 * gi.cg_score
            + 0.25 * gi.pog_score
            + 0.20 * gi.tg_score
        ))
        gi.is_anomaly = gi.combined_score >= 0.3
        out.append(gi)

    return out


def gas_score_at_tvd(indicators: List[GasIndicator], tvd: float,
                       window_ft: float = 500.0) -> float:
    if not indicators:
        return 0.0
    vals = [gi.combined_score for gi in indicators
             if abs(gi.tvd_ft - tvd) <= window_ft]
    return float(np.mean(vals)) if vals else 0.0


def gas_influence_factor(gas_units: float,
                            trend_positive: bool = False) -> float:
    """Returns ppg equivalent to ADD to PP estimate (Kuwait-tuned)."""
    if gas_units <= 0:
        return 0.0

    low_thr = get_param("gif_low_gas_threshold",
                         default=GIF_LOW_GAS_THRESHOLD)
    mod_thr = get_param("gif_mod_gas_threshold",
                         default=GIF_MOD_GAS_THRESHOLD)
    low_ppg = get_param("gif_low_ppg", default=GIF_LOW_PPG)
    mod_ppg = get_param("gif_mod_ppg", default=GIF_MOD_PPG)
    high_ppg = get_param("gif_high_ppg", default=GIF_HIGH_PPG)

    if gas_units < low_thr:
        gif = low_ppg * (gas_units / low_thr)
    elif gas_units < mod_thr:
        span = mod_thr - low_thr
        f = (gas_units - low_thr) / max(span, 1e-6)
        gif = low_ppg + f * (mod_ppg - low_ppg)
    else:
        f = min(1.0, (gas_units - mod_thr) / 200.0)
        gif = mod_ppg + f * (high_ppg - mod_ppg)

    if trend_positive and gas_units >= mod_thr:
        gif *= 1.2
    return gif


def gas_trend_positive(readings: List[GasReading],
                         n_recent: int = 3) -> bool:
    if len(readings) < n_recent + 1:
        return False
    recent = [r.total_gas_units for r in readings[-n_recent:]]
    earlier = readings[-n_recent - 1].total_gas_units
    return all(v > earlier for v in recent)
