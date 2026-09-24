"""Confidence Engine – score every reported value."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class ConfidenceInputs:
    q_pump_gpm: float = 0.0
    q_out_gpm: float = 0.0
    q_effective_gpm: float = 0.0
    bhp_model_psi: float = 0.0
    bhp_pwd_psi: Optional[float] = None
    spp_model_psi: float = 0.0
    spp_measured_psi: Optional[float] = None
    sensor_agreement: float = 1.0
    model_agreement: float = 1.0
    utube_severity: float = 0.0
    losses_fraction: float = 0.0
    kick_probability: float = 0.0
    ballooning_present: bool = False


@dataclass
class ConfidenceResult:
    bhp_confidence: float = 0.0
    ecd_confidence: float = 0.0
    pp_confidence: float = 0.0
    overall_confidence: float = 0.0
    component_scores: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def _flow_balance_score(inp: ConfidenceInputs) -> float:
    if inp.q_pump_gpm <= 0:
        return 0.5
    denom = max(inp.q_pump_gpm, 1.0)
    residual = abs(inp.q_out_gpm - inp.q_effective_gpm) / denom
    return max(0.0, 1.0 - residual / 0.10)


def _pwd_match_score(inp: ConfidenceInputs) -> Optional[float]:
    if inp.bhp_pwd_psi is None or inp.bhp_pwd_psi <= 0:
        return None
    if inp.bhp_model_psi <= 0:
        return None
    err = abs(inp.bhp_model_psi - inp.bhp_pwd_psi) / inp.bhp_pwd_psi
    return max(0.0, 1.0 - err / 0.05)


def _spp_match_score(inp: ConfidenceInputs) -> Optional[float]:
    if inp.spp_measured_psi is None or inp.spp_measured_psi <= 0:
        return None
    if inp.spp_model_psi <= 0:
        return None
    err = abs(inp.spp_model_psi - inp.spp_measured_psi) / inp.spp_measured_psi
    return max(0.0, 1.0 - err / 0.08)


def _penalties(inp: ConfidenceInputs):
    """
    Event-based confidence penalties (avoid double-counting).
    """
    p = 0.0
    w = []

    if inp.utube_severity > 0.5:
        p += 0.10 * min(1.0, (inp.utube_severity - 0.5) / 0.5)
        w.append(f"U-Tube severity {inp.utube_severity:.2f}")

    if inp.losses_fraction > 0.02:
        p += 0.15 * min(1.0, inp.losses_fraction / 0.30)
        w.append(f"Losses {inp.losses_fraction*100:.1f}%")

    # Kick penalty only if physical AND sensor DISAGREE
    if inp.kick_probability > 0.2:
        if (hasattr(inp, "bhp_pwd_psi") and inp.bhp_pwd_psi is not None):
            if inp.bhp_model_psi > 0:
                err = abs(inp.bhp_model_psi - inp.bhp_pwd_psi) / max(
                    inp.bhp_pwd_psi, 1e-6)
                if err > 0.03:
                    p += 0.15 * min(1.0, (inp.kick_probability - 0.2) / 0.6)
                    w.append(
                        f"Kick prob {inp.kick_probability*100:.0f}% "
                        f"+ PWD mismatch")
        else:
            p += 0.08 * min(1.0, (inp.kick_probability - 0.2) / 0.6)
            w.append(
                f"Kick prob {inp.kick_probability*100:.0f}% (unverified)")

    if inp.ballooning_present:
        p += 0.05
        w.append("Ballooning present")

    return min(1.0, p), w


def compute_confidence(inp: ConfidenceInputs,
                         weights: Optional[Dict[str, float]] = None
                         ) -> ConfidenceResult:
    w = weights or {
        "flow": 0.25, "pwd": 0.30, "spp": 0.15,
        "sensor": 0.15, "model": 0.15,
    }

    scores: Dict[str, float] = {}
    flow_s = _flow_balance_score(inp)
    scores["flow"] = flow_s
    pwd_s = _pwd_match_score(inp)
    spp_s = _spp_match_score(inp)

    total_w = w["flow"] + w["sensor"] + w["model"]
    weighted = (w["flow"] * flow_s
                 + w["sensor"] * inp.sensor_agreement
                 + w["model"] * inp.model_agreement)

    if pwd_s is not None:
        total_w += w["pwd"]
        weighted += w["pwd"] * pwd_s
        scores["pwd"] = pwd_s
    if spp_s is not None:
        total_w += w["spp"]
        weighted += w["spp"] * spp_s
        scores["spp"] = spp_s

    base = weighted / max(total_w, 1e-6)
    penalty, warnings = _penalties(inp)
    scores["event_penalty"] = penalty
    final = max(0.0, min(1.0, base * (1.0 - penalty)))

    return ConfidenceResult(
        bhp_confidence=final,
        ecd_confidence=final * 0.98,
        pp_confidence=final * 0.85,
        overall_confidence=final,
        component_scores=scores,
        warnings=warnings,
    )
