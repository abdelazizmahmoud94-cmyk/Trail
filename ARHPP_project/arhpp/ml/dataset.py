"""Build training datasets from synthetic signatures."""

import random
from dataclasses import dataclass, field
from typing import List, Dict

import numpy as np

from arhpp.ml.features import FEATURE_NAMES, extract_features, make_windows


@dataclass
class Dataset:
    X: np.ndarray
    y_kick: np.ndarray
    y_loss: np.ndarray
    y_anomaly: np.ndarray
    feature_names: List[str] = field(
        default_factory=lambda: list(FEATURE_NAMES))

    def __post_init__(self):
        if self.X.size == 0:
            self.X = np.zeros((0, len(FEATURE_NAMES)))
            self.y_kick = np.zeros((0,), dtype=int)
            self.y_loss = np.zeros((0,), dtype=int)
            self.y_anomaly = np.zeros((0,), dtype=int)


def _random_reading(base: Dict, noise: float = 0.02) -> Dict:
    out = {}
    for k, v in base.items():
        if isinstance(v, (int, float)):
            out[k] = v * (1.0 + random.uniform(-noise, noise))
        else:
            out[k] = v
    return out


def _make_normal_readings(n: int = 100) -> List[Dict]:
    base = {
        "q_in": 650.0, "q_out": 651.0, "spp": 3200.0,
        "rop": 45.0, "rpm": 120.0, "wob": 25.0, "torque": 18000.0,
        "mw_in": 13.5, "mw_out": 13.48, "temp_out": 180.0,
        "bg": 12.0, "cg": 0.0, "tg": 0.0, "pog": 0.0,
        "pit_volume": 4200.0, "pit_gain": 0.0,
    }
    return [_random_reading(base, noise=0.02) for _ in range(n)]


def _make_kick_readings(n: int = 100) -> List[Dict]:
    out = []
    for i in range(n):
        t = i / n
        base = {
            "q_in": 650.0, "q_out": 650.0 + 80.0 * t,
            "spp": 3200.0 - 200.0 * t,
            "rop": 45.0, "rpm": 120.0, "wob": 25.0, "torque": 18000.0,
            "mw_in": 13.5, "mw_out": 13.5 - 1.5 * t, "temp_out": 180.0,
            "bg": 12.0 + 60.0 * t, "cg": 0.0, "tg": 0.0, "pog": 0.0,
            "pit_volume": 4200.0 + 20.0 * t, "pit_gain": 15.0 * t,
        }
        out.append(_random_reading(base, noise=0.03))
    return out


def _make_loss_readings(n: int = 100) -> List[Dict]:
    out = []
    for i in range(n):
        t = i / n
        base = {
            "q_in": 650.0, "q_out": 650.0 - 120.0 * t,
            "spp": 3200.0 - 400.0 * t,
            "rop": 45.0, "rpm": 120.0, "wob": 25.0, "torque": 18000.0,
            "mw_in": 13.5, "mw_out": 13.5, "temp_out": 180.0,
            "bg": 12.0, "cg": 0.0, "tg": 0.0, "pog": 0.0,
            "pit_volume": 4200.0 - 20.0 * t, "pit_gain": -5.0 * t,
        }
        out.append(_random_reading(base, noise=0.03))
    return out


def _make_packoff_readings(n: int = 100) -> List[Dict]:
    out = []
    for i in range(n):
        t = i / n
        base = {
            "q_in": 650.0, "q_out": 650.0 - 100.0 * t,
            "spp": 3200.0 + 900.0 * t,
            "rop": 45.0 - 25.0 * t, "rpm": 120.0,
            "wob": 25.0 + 5.0 * t, "torque": 18000.0 + 6000.0 * t,
            "mw_in": 13.5, "mw_out": 13.5, "temp_out": 180.0,
            "bg": 12.0, "cg": 0.0, "tg": 0.0, "pog": 0.0,
            "pit_volume": 4200.0, "pit_gain": 0.0,
        }
        out.append(_random_reading(base, noise=0.03))
    return out


def _make_washout_readings(n: int = 100) -> List[Dict]:
    out = []
    for i in range(n):
        t = i / n
        base = {
            "q_in": 650.0, "q_out": 655.0,
            "spp": 3200.0 - 500.0 * t + random.uniform(-80, 80),
            "rop": 45.0, "rpm": 120.0, "wob": 25.0, "torque": 18000.0,
            "mw_in": 13.5, "mw_out": 13.5, "temp_out": 180.0,
            "bg": 12.0, "cg": 0.0, "tg": 0.0, "pog": 0.0,
            "pit_volume": 4200.0, "pit_gain": 0.0,
        }
        out.append(_random_reading(base, noise=0.05))
    return out


def build_synthetic_dataset(n_per_class: int = 200,
                              window_size: int = 60,
                              stride: int = 20,
                              seed: int = 42) -> Dataset:
    random.seed(seed)
    np.random.seed(seed)
    classes = [
        ("normal", _make_normal_readings, 0, 0, 0),
        ("kick", _make_kick_readings, 1, 0, 1),
        ("loss", _make_loss_readings, 0, 1, 1),
        ("packoff", _make_packoff_readings, 0, 0, 1),
        ("washout", _make_washout_readings, 0, 0, 1),
    ]
    X, y_k, y_l, y_a = [], [], [], []
    for _, gen_fn, lk, ll, la in classes:
        readings = gen_fn(n_per_class)
        windows = make_windows(readings, window_size, stride)
        for w in windows:
            X.append([w["features"].get(k, 0.0) for k in FEATURE_NAMES])
            y_k.append(lk)
            y_l.append(ll)
            y_a.append(la)
    return Dataset(
        X=np.array(X, dtype=float),
        y_kick=np.array(y_k, dtype=int),
        y_loss=np.array(y_l, dtype=int),
        y_anomaly=np.array(y_a, dtype=int),
    )
