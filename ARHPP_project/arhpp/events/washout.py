"""Washout Engine — SPP drop with unstable flow behaviour."""

from dataclasses import dataclass, field
from typing import List

from arhpp.core.constants import WASHOUT_SPP_DROP_FRAC


@dataclass
class WashoutInputs:
    spp_baseline_psi: float = 0.0
    spp_current_psi: float = 0.0
    spp_noise_std_psi: float = 0.0
    flow_in_gpm: float = 0.0
    flow_out_gpm: float = 0.0
    q_step_gpm: float = 0.0
    spp_response_ratio: float = 1.0


@dataclass
class WashoutResult:
    probability: float = 0.0
    risk: str = "none"
    spp_drop_frac: float = 0.0
    spp_noise_ratio: float = 0.0
    q_response_ratio: float = 1.0
    reasons: List[str] = field(default_factory=list)


def compute_washout(inp: WashoutInputs) -> WashoutResult:
    r = WashoutResult()
    if inp.spp_baseline_psi > 0:
        r.spp_drop_frac = max(
            0.0,
            (inp.spp_baseline_psi - inp.spp_current_psi)
            / inp.spp_baseline_psi)
        r.spp_noise_ratio = (inp.spp_noise_std_psi
                                / inp.spp_baseline_psi)
    r.q_response_ratio = inp.spp_response_ratio

    score = 0.0
    wsum = 0.0
    if r.spp_drop_frac >= WASHOUT_SPP_DROP_FRAC:
        score += 0.45 * min(1.0, r.spp_drop_frac / 0.3)
    wsum += 0.45
    if r.spp_noise_ratio >= 0.02:
        score += 0.20 * min(1.0, r.spp_noise_ratio / 0.08)
    wsum += 0.20
    if r.q_response_ratio < 0.7:
        score += 0.20 * (1.0 - r.q_response_ratio / 0.7)
    wsum += 0.20
    if inp.flow_in_gpm > 0 and inp.flow_out_gpm > 0:
        imb = abs(inp.flow_in_gpm - inp.flow_out_gpm) / inp.flow_in_gpm
        if imb >= 0.05:
            score += 0.15 * min(1.0, imb / 0.2)
    wsum += 0.15

    r.probability = score / wsum if wsum > 0 else 0.0

    if r.probability < 0.20:
        r.risk = "none"
    elif r.probability < 0.45:
        r.risk = "low"
    elif r.probability < 0.70:
        r.risk = "moderate"
    else:
        r.risk = "high"

    if r.spp_drop_frac >= WASHOUT_SPP_DROP_FRAC:
        r.reasons.append(f"SPP -{r.spp_drop_frac*100:.1f}%")
    if r.spp_noise_ratio >= 0.02:
        r.reasons.append(f"SPP noise {r.spp_noise_ratio*100:.1f}%")
    if r.q_response_ratio < 0.7:
        r.reasons.append(f"Q response ratio {r.q_response_ratio:.2f}")
    return r
