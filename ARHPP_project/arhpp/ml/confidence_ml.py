"""ML-enhanced confidence score."""

from dataclasses import dataclass
from typing import Optional

from arhpp.meta.confidence import (
    ConfidenceResult,
)


@dataclass
class MLConfidenceInputs:
    physics_result: Optional[ConfidenceResult] = None
    anomaly_score: float = 0.0
    kick_prob_ml: float = 0.0
    kick_prob_physics: float = 0.0
    loss_prob_ml: float = 0.0
    loss_prob_physics: float = 0.0


def compute_ml_confidence(inp: MLConfidenceInputs,
                            w_physics: float = 0.60,
                            w_ml: float = 0.40) -> ConfidenceResult:
    base = inp.physics_result or ConfidenceResult()
    agree_kick = 1.0 - abs(inp.kick_prob_ml - inp.kick_prob_physics)
    agree_loss = 1.0 - abs(inp.loss_prob_ml - inp.loss_prob_physics)
    agreement = (agree_kick + agree_loss) / 2.0
    anomaly_penalty = max(0.0, inp.anomaly_score) * 0.5
    ml_conf = max(0.0, agreement - anomaly_penalty)
    final = w_physics * base.overall_confidence + w_ml * ml_conf
    final = max(0.0, min(1.0, final))

    out = ConfidenceResult(
        bhp_confidence=final,
        ecd_confidence=final * 0.98,
        pp_confidence=final * 0.85,
        overall_confidence=final,
        component_scores=dict(base.component_scores),
        warnings=list(base.warnings))
    out.component_scores["ml_agreement"] = agreement
    out.component_scores["ml_anomaly_penalty"] = anomaly_penalty
    out.component_scores["ml_confidence"] = ml_conf
    if inp.anomaly_score > 0.6:
        out.warnings.append(f"ML anomaly score high ({inp.anomaly_score:.2f})")
    if agreement < 0.6:
        out.warnings.append(f"Physics-ML disagreement ({agreement:.2f})")
    return out
