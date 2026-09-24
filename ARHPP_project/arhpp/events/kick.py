"""Kick Engine — detect, size, and evaluate BHP impact of an influx.

Calibrated weights and thresholds are read from the context.
"""

from dataclasses import dataclass, field
from typing import List

from arhpp.core.constants import (
    PSI_PER_FT_PER_PPG,
    KICK_FLOW_IMBALANCE_GPM, KICK_PIT_GAIN_BBL,
    KICK_CONNECTION_GAS_UNITS, KICK_BG_GAS_UNITS,
)
from arhpp.calibration.context import get_param


@dataclass
class KickInputs:
    q_in_gpm: float = 0.0
    q_out_gpm: float = 0.0
    pit_gain_bbl: float = 0.0
    connection_gas_units: float = 0.0
    background_gas_units: float = 0.0
    trip_gas_units: float = 0.0
    pumps_off: bool = False
    tvd_ft: float = 0.0
    mw_ppg: float = 10.0
    mw_in_ppg: float = 10.0
    mw_out_ppg: float = 10.0
    annular_fp_psi: float = 0.0
    sbp_psi: float = 0.0


@dataclass
class KickResult:
    probability: float = 0.0
    severity: str = "none"
    influx_type: str = "unknown"
    influx_volume_bbl: float = 0.0
    kick_rate_gpm: float = 0.0
    hydrostatic_reduction_psi: float = 0.0
    bhp_reduction_psi: float = 0.0
    ecd_reduction_ppg: float = 0.0
    sicp_estimate_psi: float = 0.0
    sitp_estimate_psi: float = 0.0
    reasons: List[str] = field(default_factory=list)


def _flow_p(imb: float, thr: float = KICK_FLOW_IMBALANCE_GPM) -> float:
    if imb <= 0:
        return 0.0
    if imb < thr:
        return 0.3 * (imb / thr)
    return min(1.0, 0.3 + 0.7 * (imb / (thr * 4.0)))


def _pit_p(pit: float, thr: float = KICK_PIT_GAIN_BBL) -> float:
    if pit <= 0:
        return 0.0
    if pit < thr:
        return 0.4 * (pit / thr)
    return min(1.0, 0.4 + 0.6 * (pit / (thr * 4.0)))


def _gas_p(cg: float, bg: float, tg: float,
             thr: float = 20.0) -> float:
    p = 0.0
    if bg > thr:
        p = max(p, 0.25 * min(1.0, bg / (thr * 3.0)))
    if cg > thr:
        p = max(p, 0.55 * min(1.0, cg / (thr * 3.0)))
    if tg > thr:
        p = max(p, 0.65 * min(1.0, tg / (thr * 3.0)))
    return p


def _classify_influx_enhanced(cg, bg, tg, pit_gain,
                                mw_in, mw_out, q_in, q_out) -> str:
    """Enhanced influx classifier."""
    mw_drop = mw_in - mw_out if mw_in > 0 else 0.0
    has_gas = (bg > 20 or cg > 50 or tg > 80)
    has_pit_gain = pit_gain > 0

    if has_gas and mw_drop > 0.5:
        return "gas"
    if has_gas and has_pit_gain and mw_drop > 0.2:
        return "gas"
    if has_pit_gain and not has_gas and abs(mw_drop) < 0.3:
        return "water"
    if has_pit_gain and 0.1 < mw_drop < 0.5:
        return "oil"
    if has_gas:
        return "gas"
    return "unknown"


def compute_kick(inp: KickInputs,
                   kick_duration_min: float = 0.0) -> KickResult:
    r = KickResult()

    # Calibrated weights from context
    w_flow = get_param("kick_w_flow", default=0.40)
    w_pit = get_param("kick_w_pit", default=0.35)
    w_gas = get_param("kick_w_gas", default=0.25)

    total_w = w_flow + w_pit + w_gas
    if total_w > 0:
        w_flow /= total_w
        w_pit /= total_w
        w_gas /= total_w

    flow_thr = get_param("kick_flow_threshold_gpm",
                          default=KICK_FLOW_IMBALANCE_GPM)
    pit_thr = get_param("kick_pit_threshold_bbl",
                         default=KICK_PIT_GAIN_BBL)
    gas_thr = get_param("kick_gas_threshold_units", default=20.0)

    imb = max(0.0, inp.q_out_gpm - inp.q_in_gpm)
    p_flow = _flow_p(imb, flow_thr)
    p_pit = _pit_p(inp.pit_gain_bbl, pit_thr)
    p_gas = _gas_p(inp.connection_gas_units, inp.background_gas_units,
                    inp.trip_gas_units, gas_thr)

    r.probability = min(1.0,
                         w_flow * p_flow + w_pit * p_pit + w_gas * p_gas)

    r.influx_type = _classify_influx_enhanced(
        inp.connection_gas_units, inp.background_gas_units,
        inp.trip_gas_units, inp.pit_gain_bbl,
        inp.mw_in_ppg or inp.mw_ppg, inp.mw_out_ppg or inp.mw_ppg,
        inp.q_in_gpm, inp.q_out_gpm)

    r.kick_rate_gpm = imb
    r.influx_volume_bbl = (max(0.0, inp.pit_gain_bbl)
                            + max(0.0, imb) * max(0.0, kick_duration_min) / 42.0)

    if r.probability < 0.2:
        r.severity = "none"
    elif r.probability < 0.45:
        r.severity = "minor"
    elif r.probability < 0.7:
        r.severity = "moderate"
    elif r.probability < 0.9:
        r.severity = "severe"
    else:
        r.severity = "blowout-risk"

    if r.influx_volume_bbl > 0 and inp.tvd_ft > 0:
        cap = 0.0459
        h = min(r.influx_volume_bbl / max(cap, 1e-4), inp.tvd_ft)
        rho_in = {"gas": 1.0, "oil": 6.5, "water": 8.6,
                   "mixed": 4.0}.get(r.influx_type, 4.0)
        drho = max(0.0, inp.mw_ppg - rho_in)
        r.hydrostatic_reduction_psi = PSI_PER_FT_PER_PPG * drho * h
        r.bhp_reduction_psi = r.hydrostatic_reduction_psi
        r.ecd_reduction_ppg = (r.hydrostatic_reduction_psi
                                 / (PSI_PER_FT_PER_PPG * inp.tvd_ft))

    if inp.pumps_off or imb > 0:
        r.sicp_estimate_psi = (0.5 * inp.annular_fp_psi
                                 + 5.0 * imb
                                 + r.hydrostatic_reduction_psi * 0.3)
        r.sitp_estimate_psi = max(
            0.0, r.sicp_estimate_psi - 0.3 * r.hydrostatic_reduction_psi)

    if p_flow > 0.3:
        r.reasons.append(f"Flow imbalance {imb:.1f} gpm")
    if p_pit > 0.3:
        r.reasons.append(f"Pit gain {inp.pit_gain_bbl:.2f} bbl")
    if p_gas > 0.3:
        r.reasons.append("Gas readings elevated")

    return r
