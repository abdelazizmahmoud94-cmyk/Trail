"""Pack-Off Engine — SPP rise + torque rise + drag rise + flow deficit."""

from dataclasses import dataclass, field
from typing import List

from arhpp.core.constants import (
    PACKOFF_SPP_RISE_FRAC, PACKOFF_TORQUE_RISE_FRAC, PACKOFF_DRAG_RISE_FRAC,
)


@dataclass
class PackOffInputs:
    spp_baseline_psi: float = 0.0
    spp_current_psi: float = 0.0
    torque_baseline_ftlb: float = 0.0
    torque_current_ftlb: float = 0.0
    drag_baseline_klb: float = 0.0
    drag_current_klb: float = 0.0
    flow_in_gpm: float = 0.0
    flow_out_gpm: float = 0.0


@dataclass
class PackOffResult:
    probability: float = 0.0
    risk: str = "none"
    spp_rise_frac: float = 0.0
    torque_rise_frac: float = 0.0
    drag_rise_frac: float = 0.0
    flow_deficit_frac: float = 0.0
    restriction_percent: float = 0.0
    reasons: List[str] = field(default_factory=list)


def _frac(a: float, b: float) -> float:
    return (a - b) / b if b > 1e-9 else 0.0


def compute_packoff(inp: PackOffInputs) -> PackOffResult:
    r = PackOffResult()
    r.spp_rise_frac = _frac(inp.spp_current_psi, inp.spp_baseline_psi)
    r.torque_rise_frac = _frac(inp.torque_current_ftlb,
                                 inp.torque_baseline_ftlb)
    r.drag_rise_frac = _frac(inp.drag_current_klb,
                               inp.drag_baseline_klb)
    if inp.flow_in_gpm > 0:
        r.flow_deficit_frac = max(
            0.0, (inp.flow_in_gpm - inp.flow_out_gpm) / inp.flow_in_gpm)

    if inp.spp_current_psi > inp.spp_baseline_psi > 0:
        r.restriction_percent = 100.0 * (
            1.0 - (inp.spp_baseline_psi / inp.spp_current_psi) ** 0.5)
        r.restriction_percent = max(0.0, min(99.0, r.restriction_percent))

    score = 0.0
    wsum = 0.0
    if r.spp_rise_frac >= PACKOFF_SPP_RISE_FRAC:
        score += 0.35 * min(1.0, r.spp_rise_frac / 0.5)
    wsum += 0.35
    if r.torque_rise_frac >= PACKOFF_TORQUE_RISE_FRAC:
        score += 0.30 * min(1.0, r.torque_rise_frac / 0.6)
    wsum += 0.30
    if r.drag_rise_frac >= PACKOFF_DRAG_RISE_FRAC:
        score += 0.20 * min(1.0, r.drag_rise_frac / 0.8)
    wsum += 0.20
    if r.flow_deficit_frac >= 0.10:
        score += 0.15 * min(1.0, r.flow_deficit_frac / 0.3)
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

    if r.spp_rise_frac >= PACKOFF_SPP_RISE_FRAC:
        r.reasons.append(f"SPP +{r.spp_rise_frac*100:.1f}%")
    if r.torque_rise_frac >= PACKOFF_TORQUE_RISE_FRAC:
        r.reasons.append(f"Torque +{r.torque_rise_frac*100:.1f}%")
    if r.drag_rise_frac >= PACKOFF_DRAG_RISE_FRAC:
        r.reasons.append(f"Drag +{r.drag_rise_frac*100:.1f}%")
    if r.flow_deficit_frac >= 0.10:
        r.reasons.append(f"Flow deficit {r.flow_deficit_frac*100:.1f}%")
    return r
