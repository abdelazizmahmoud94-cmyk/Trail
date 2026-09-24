"""Unsupervised anomaly detection via Isolation Forest."""

from dataclasses import dataclass
from typing import List, Optional, Dict

import numpy as np

from arhpp.ml.features import FEATURE_NAMES


@dataclass
class AnomalyResult:
    is_anomaly: bool = False
    score: float = 0.0
    normalized_score: float = 0.0
    top_features: List[tuple] = None

    def __post_init__(self):
        if self.top_features is None:
            self.top_features = []


class AnomalyDetector:
    def __init__(self, contamination: float = 0.10,
                 n_estimators: int = 100,
                 random_state: int = 42):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model = None
        self.mean = None
        self.std = None
        self.is_fitted = False

    def fit(self, X: np.ndarray) -> "AnomalyDetector":
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            raise RuntimeError("scikit-learn required for ML layer")

        self.mean = X.mean(axis=0)
        self.std = X.std(axis=0) + 1e-9
        Xn = (X - self.mean) / self.std

        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1)
        self.model.fit(Xn)
        self.is_fitted = True
        return self

    def predict_one(self, features: Dict[str, float]) -> AnomalyResult:
        if not self.is_fitted:
            return AnomalyResult()
        x = np.array([[features.get(k, 0.0) for k in FEATURE_NAMES]])
        xn = (x - self.mean) / self.std
        score = float(self.model.score_samples(xn)[0])
        pred = int(self.model.predict(xn)[0])
        norm = max(0.0, min(1.0, (-score) / 0.5))
        z = np.abs((x[0] - self.mean) / self.std)
        idx = np.argsort(z)[::-1][:5]
        top = [(FEATURE_NAMES[i], float(z[i])) for i in idx]
        return AnomalyResult(
            is_anomaly=(pred == -1),
            score=score,
            normalized_score=norm,
            top_features=top)


def default_detector() -> AnomalyDetector:
    from arhpp.ml.dataset import build_synthetic_dataset
    ds = build_synthetic_dataset(n_per_class=200)
    det = AnomalyDetector(contamination=0.10)
    det.fit(ds.X)
    return det
