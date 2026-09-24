"""Training pipeline for all ML models."""

from dataclasses import dataclass, field
from typing import List, Optional
import time

import numpy as np

from arhpp.ml.dataset import build_synthetic_dataset, Dataset
from arhpp.ml.anomaly import AnomalyDetector
from arhpp.ml.kick_classifier import KickClassifier, LossClassifier
from arhpp.ml.persist import save_model


@dataclass
class TrainingReport:
    n_samples: int = 0
    n_features: int = 0
    anomaly_contamination: float = 0.0
    kick_accuracy: float = 0.0
    loss_accuracy: float = 0.0
    elapsed_s: float = 0.0
    model_paths: List[str] = field(default_factory=list)


def _train_test_split(X, y, test_frac: float = 0.25, seed: int = 42):
    rng = np.random.RandomState(seed)
    n = len(X)
    idx = rng.permutation(n)
    cut = int(n * (1 - test_frac))
    return X[idx[:cut]], y[idx[:cut]], X[idx[cut:]], y[idx[cut:]]


def _accuracy(model, X_test, y_test) -> float:
    if len(X_test) == 0:
        return 0.0
    preds = model.predict(X_test)
    return float((preds == y_test).mean())


def train_all(dataset: Optional[Dataset] = None,
                n_per_class: int = 250,
                test_frac: float = 0.25,
                verbose: bool = True) -> TrainingReport:
    t0 = time.time()
    if dataset is None:
        dataset = build_synthetic_dataset(n_per_class=n_per_class)
    if verbose:
        print(f"  Dataset: {dataset.X.shape[0]} samples x "
                f"{dataset.X.shape[1]} features")

    report = TrainingReport(
        n_samples=dataset.X.shape[0],
        n_features=dataset.X.shape[1])

    if verbose:
        print("\n  [1/3] Training anomaly detector...")
    det = AnomalyDetector(contamination=0.10)
    det.fit(dataset.X)
    report.anomaly_contamination = det.contamination
    p = save_model(det, "anomaly_detector")
    report.model_paths.append(str(p))

    if verbose:
        print("\n  [2/3] Training kick classifier...")
    Xtr, ytr, Xte, yte = _train_test_split(
        dataset.X, dataset.y_kick, test_frac=test_frac)
    kc = KickClassifier()
    kc.fit(Xtr, ytr)
    report.kick_accuracy = _accuracy(kc.model, Xte, yte)
    p = save_model(kc, "kick_classifier")
    report.model_paths.append(str(p))
    if verbose:
        print(f"        test accuracy = {report.kick_accuracy*100:.2f}%")

    if verbose:
        print("\n  [3/3] Training loss classifier...")
    Xtr, ytr, Xte, yte = _train_test_split(
        dataset.X, dataset.y_loss, test_frac=test_frac)
    lc = LossClassifier()
    lc.fit(Xtr, ytr)
    report.loss_accuracy = _accuracy(lc.model, Xte, yte)
    p = save_model(lc, "loss_classifier")
    report.model_paths.append(str(p))
    if verbose:
        print(f"        test accuracy = {report.loss_accuracy*100:.2f}%")

    report.elapsed_s = time.time() - t0
    if verbose:
        print(f"\n  Total time: {report.elapsed_s:.2f}s")
    return report
