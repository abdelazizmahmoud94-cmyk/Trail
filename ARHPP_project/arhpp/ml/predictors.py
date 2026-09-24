"""Runtime ML inference — lazy loading."""

import threading
from dataclasses import dataclass
from typing import Optional, Dict, List

from arhpp.ml.anomaly import AnomalyDetector, AnomalyResult
from arhpp.ml.kick_classifier import (
    KickClassifier, LossClassifier, ClassificationResult,
)
from arhpp.ml.confidence_ml import MLConfidenceInputs, compute_ml_confidence
from arhpp.ml.persist import load_model, has_model
from arhpp.meta.confidence import ConfidenceResult


@dataclass
class MLPrediction:
    anomaly: AnomalyResult = None
    kick: ClassificationResult = None
    loss: ClassificationResult = None
    ml_confidence: Optional[ConfidenceResult] = None

    def __post_init__(self):
        if self.anomaly is None:
            self.anomaly = AnomalyResult()
        if self.kick is None:
            self.kick = ClassificationResult()
        if self.loss is None:
            self.loss = ClassificationResult()


class MLPredictor:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.anomaly: Optional[AnomalyDetector] = None
        self.kick: Optional[KickClassifier] = None
        self.loss: Optional[LossClassifier] = None
        self._load_lock = threading.Lock()
        self._loaded = False

    @classmethod
    def get(cls) -> "MLPredictor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            self._load()
            self._loaded = True

    def _load(self) -> None:
        if has_model("anomaly_detector"):
            self.anomaly = load_model("anomaly_detector")
        if has_model("kick_classifier"):
            self.kick = load_model("kick_classifier")
        if has_model("loss_classifier"):
            self.loss = load_model("loss_classifier")
        if self.anomaly is None:
            from arhpp.ml.anomaly import default_detector
            self.anomaly = default_detector()

    def is_ready(self) -> bool:
        return self._loaded

    def predict(self, features: Dict[str, float],
                  physics_confidence: Optional[ConfidenceResult] = None,
                  physics_kick_prob: float = 0.0,
                  physics_loss_prob: float = 0.0) -> MLPrediction:
        self._ensure_loaded()
        out = MLPrediction()
        if self.anomaly:
            out.anomaly = self.anomaly.predict_one(features)
        if self.kick:
            out.kick = self.kick.predict_one(features)
        if self.loss:
            out.loss = self.loss.predict_one(features)
        if physics_confidence is not None:
            out.ml_confidence = compute_ml_confidence(MLConfidenceInputs(
                physics_result=physics_confidence,
                anomaly_score=out.anomaly.normalized_score,
                kick_prob_ml=out.kick.probability,
                kick_prob_physics=physics_kick_prob,
                loss_prob_ml=out.loss.probability,
                loss_prob_physics=physics_loss_prob))
        return out
