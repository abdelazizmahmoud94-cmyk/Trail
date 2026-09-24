"""Feature extraction — SENSOR-ONLY (no physics leakage)."""

from dataclasses import dataclass, field
from typing import List, Dict

import numpy as np


FEATURE_NAMES = [
    "q_in_mean", "q_in_std", "q_in_trend",
    "q_out_mean", "q_out_std", "q_out_trend",
    "dq_mean", "dq_std", "dq_trend",
    "spp_mean", "spp_std", "spp_trend", "spp_norm_std",
    "rop_mean", "rop_trend", "rop_std",
    "rpm_mean", "rpm_std",
    "wob_mean", "wob_trend",
    "torque_mean", "torque_trend", "torque_std",
    "mw_in_mean", "mw_out_mean", "mw_diff_mean", "mw_diff_trend",
    "temp_out_mean", "temp_out_trend",
    "bg_mean", "bg_max", "bg_trend",
    "cg_mean", "cg_max",
    "tg_mean", "tg_max",
    "pog_mean", "pog_max",
    "pit_volume_mean", "pit_volume_trend",
    "pit_gain_mean", "pit_gain_max",
    "q_ratio", "mw_ratio", "spp_per_q",
    "dq_per_qin", "gas_per_q",
]


@dataclass
class FeatureWindow:
    well_id: str = ""
    timestamp_start: str = ""
    timestamp_end: str = ""
    label_kick: int = 0
    label_loss: int = 0
    label_anomaly: int = 0
    features: Dict[str, float] = field(default_factory=dict)

    def to_vector(self) -> List[float]:
        return [self.features.get(k, 0.0) for k in FEATURE_NAMES]


def _trend(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    k = len(values)
    x_mean = (k - 1) / 2.0
    y_mean = sum(values) / k
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(k))
    return num / den if den > 0 else 0.0


def _safe_mean(vals):
    return float(np.mean(vals)) if vals else 0.0


def _safe_std(vals):
    return float(np.std(vals)) if len(vals) > 1 else 0.0


def _safe_max(vals):
    return float(np.max(vals)) if vals else 0.0


def extract_features(readings: List[dict]) -> Dict[str, float]:
    """Extract SENSOR-ONLY features (no physics outputs)."""
    if not readings:
        return {k: 0.0 for k in FEATURE_NAMES}

    def col(key: str) -> List[float]:
        return [float(r.get(key, 0.0) or 0.0) for r in readings]

    q_in = col("q_in")
    q_out = col("q_out")
    dq = [o - i for i, o in zip(q_in, q_out)]
    spp = col("spp")
    rop = col("rop")
    rpm = col("rpm")
    wob = col("wob")
    torque = col("torque")
    mw_in = col("mw_in")
    mw_out = col("mw_out")
    mw_diff = [o - i for i, o in zip(mw_in, mw_out)]
    temp_out = col("temp_out")
    bg = col("bg")
    cg = col("cg")
    tg = col("tg")
    pog = col("pog")
    pit_vol = col("pit_volume")
    pit_gain = col("pit_gain")

    f = {}
    f["q_in_mean"] = _safe_mean(q_in)
    f["q_in_std"] = _safe_std(q_in)
    f["q_in_trend"] = _trend(q_in)
    f["q_out_mean"] = _safe_mean(q_out)
    f["q_out_std"] = _safe_std(q_out)
    f["q_out_trend"] = _trend(q_out)
    f["dq_mean"] = _safe_mean(dq)
    f["dq_std"] = _safe_std(dq)
    f["dq_trend"] = _trend(dq)

    f["spp_mean"] = _safe_mean(spp)
    f["spp_std"] = _safe_std(spp)
    f["spp_trend"] = _trend(spp)
    f["spp_norm_std"] = f["spp_std"] / max(abs(f["spp_mean"]), 1.0)

    f["rop_mean"] = _safe_mean(rop)
    f["rop_trend"] = _trend(rop)
    f["rop_std"] = _safe_std(rop)
    f["rpm_mean"] = _safe_mean(rpm)
    f["rpm_std"] = _safe_std(rpm)
    f["wob_mean"] = _safe_mean(wob)
    f["wob_trend"] = _trend(wob)
    f["torque_mean"] = _safe_mean(torque)
    f["torque_trend"] = _trend(torque)
    f["torque_std"] = _safe_std(torque)

    f["mw_in_mean"] = _safe_mean(mw_in)
    f["mw_out_mean"] = _safe_mean(mw_out)
    f["mw_diff_mean"] = _safe_mean(mw_diff)
    f["mw_diff_trend"] = _trend(mw_diff)
    f["temp_out_mean"] = _safe_mean(temp_out)
    f["temp_out_trend"] = _trend(temp_out)

    f["bg_mean"] = _safe_mean(bg)
    f["bg_max"] = _safe_max(bg)
    f["bg_trend"] = _trend(bg)
    f["cg_mean"] = _safe_mean(cg)
    f["cg_max"] = _safe_max(cg)
    f["tg_mean"] = _safe_mean(tg)
    f["tg_max"] = _safe_max(tg)
    f["pog_mean"] = _safe_mean(pog)
    f["pog_max"] = _safe_max(pog)

    f["pit_volume_mean"] = _safe_mean(pit_vol)
    f["pit_volume_trend"] = _trend(pit_vol)
    f["pit_gain_mean"] = _safe_mean(pit_gain)
    f["pit_gain_max"] = _safe_max(pit_gain)

    f["q_ratio"] = f["q_out_mean"] / max(f["q_in_mean"], 1.0)
    f["mw_ratio"] = f["mw_out_mean"] / max(f["mw_in_mean"], 1.0)
    f["spp_per_q"] = f["spp_mean"] / max(f["q_in_mean"], 1.0)
    f["dq_per_qin"] = f["dq_mean"] / max(f["q_in_mean"], 1.0)
    f["gas_per_q"] = f["bg_mean"] / max(f["q_in_mean"], 1.0)

    return f


def make_windows(readings: List[dict], window_size: int = 60,
                   stride: int = 15) -> List[Dict]:
    out = []
    if len(readings) < window_size:
        return [{"start": 0, "end": len(readings),
                  "features": extract_features(readings)}]
    for start in range(0, len(readings) - window_size + 1, stride):
        chunk = readings[start:start + window_size]
        out.append({
            "start": start,
            "end": start + window_size,
            "features": extract_features(chunk),
        })
    return out
