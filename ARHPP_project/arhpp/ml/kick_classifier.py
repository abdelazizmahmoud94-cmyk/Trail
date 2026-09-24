"""Supervised kick / loss classification with Random Forest."""

from dataclasses import dataclass, field
from typing import List, Dict

import numpy as np

from arhpp.ml.features import FEATURE_NAMES


@dataclass
class ClassificationResult:
    probability: float = 0.0
    predicted_class: int = 0
    feature_importance: List[tuple] = field(default_factory=list)
    confidence: float = 0.0


class KickClassifier:
    def __init__(self, n_estimators: int = 200, max_depth: int = 10,
                 random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.model = None
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "KickClassifier":
        try:
            from sklearn.ensemble import RandomForestClassifier
        except ImportError:
            raise RuntimeError("scikit-learn required")

        pos = int(y.sum())
        neg = int(len(y) - pos)
        class_weight = ({0: 1.0, 1: max(1.0, neg / max(pos, 1))}
                         if pos > 0 else None)

        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.random_state,
            class_weight=class_weight,
            n_jobs=-1)
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict_one(self, features: Dict[str, float]) -> ClassificationResult:
        if not self.is_fitted:
            return ClassificationResult()
        x = np.array([[features.get(k, 0.0) for k in FEATURE_NAMES]])
        proba = self.model.predict_proba(x)[0]
        pred = int(np.argmax(proba))
        p = float(proba[1]) if len(proba) > 1 else float(proba[0])
        imps = self.model.feature_importances_
        idx = np.argsort(imps)[::-1][:5]
        fi = [(FEATURE_NAMES[i], float(imps[i])) for i in idx]
        return ClassificationResult(
            probability=p,
            predicted_class=pred,
            feature_importance=fi,
            confidence=abs(p - 0.5) * 2.0)


class LossClassifier(KickClassifier):
    pass
