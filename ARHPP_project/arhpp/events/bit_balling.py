"""Bit Balling Engine — SPP rise + torque rise + ROP drop + WOB rise."""

from dataclasses import dataclass, field
from typing import List

from arhpp.core.constants import (
    BALLING_SPP_RISE_FRAC, BALLING_TORQUE_RISE_FRAC, BALLING_ROP_DROP_FRAC,
)


@dataclass
class BitBallingInputs:
    spp_baseline_psi: float = 0.0
    spp_current_psi: float = 0.0
    torque_baseline_ftlb: float = 0.0
    torque_current_ftlb: float = 0.0
    rop_baseline_ft_hr: float = 0.0
    rop_current_ft_hr: float = 0.0
    wob_baseline_klb: float = 0.0
    wob_current_klb: float = 0.0
    formation: str = "shale"
    mud_type: str = "WBM"


@dataclass
class BitBallingResult:
    risk: str = "none"
    probability: float = 0.0
    spp_rise_frac: float = 0.0
    torque_rise_frac: float = 0.0
    rop_drop_frac: float = 0.0
    wob_rise_frac: float = 0.0
    reasons: List[str] = field(default_factory=list)


def _frac(a: float, b: float) -> float:
    return (a - b) / b if b > 1e-9 else 0.0


def compute_bit_balling(inp: BitBallingInputs) -> BitBallingResult:
    r = BitBallingResult()
    r.spp_rise_frac = _frac(inp.spp_current_psi, inp.spp_baseline_psi)
    r.torque_rise_frac = _frac(inp.torque_current_ftlb,
                                 inp.torque_baseline_ftlb)
    r.rop_drop_frac = -_frac(inp.rop_current_ft_hr,
                               inp.rop_baseline_ft_hr)
    r.wob_rise_frac = _frac(inp.wob_current_klb, inp.wob_baseline_klb)

    score = 0.0
    wsum = 0.0
    if r.spp_rise_frac >= BALLING_SPP_RISE_FRAC:
        score += 0.30 * min(1.0, r.spp_rise_frac / 0.4)
    wsum += 0.30
    if r.torque_rise_frac >= BALLING_TORQUE_RISE_FRAC:
        score += 0.30 * min(1.0, r.torque_rise_frac / 0.5)
    wsum += 0.30
    if r.rop_drop_frac >= BALLING_ROP_DROP_FRAC:
        score += 0.25 * min(1.0, r.rop_drop_frac / 0.6)
    wsum += 0.25
    if r.wob_rise_frac >= 0.20:
        score += 0.15 * min(1.0, r.wob_rise_frac / 0.5)
    wsum += 0.15

    base = score / wsum if wsum > 0 else 0.0
    fm = 1.0
    if inp.formation.lower() == "shale":
        fm *= 1.3
    if inp.mud_type.upper() == "WBM":
        fm *= 1.2
    elif inp.mud_type.upper() == "OBM":
        fm *= 0.75

    r.probability = min(1.0, base * fm)

    if r.probability < 0.25:
        r.risk = "none"
    elif r.probability < 0.5:
        r.risk = "low"
    elif r.probability < 0.75:
        r.risk = "moderate"
    else:
        r.risk = "high"

    if r.spp_rise_frac >= BALLING_SPP_RISE_FRAC:
        r.reasons.append(f"SPP +{r.spp_rise_frac*100:.1f}%")
    if r.torque_rise_frac >= BALLING_TORQUE_RISE_FRAC:
        r.reasons.append(f"Torque +{r.torque_rise_frac*100:.1f}%")
    if r.rop_drop_frac >= BALLING_ROP_DROP_FRAC:
        r.reasons.append(f"ROP -{r.rop_drop_frac*100:.1f}%")
    if r.wob_rise_frac >= 0.20:
        r.reasons.append(f"WOB +{r.wob_rise_frac*100:.1f}%")
    return r
