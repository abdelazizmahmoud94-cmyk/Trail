"""Dashboard Engine – aggregate every layer into one report."""

from dataclasses import dataclass, field
from typing import Optional, List

from arhpp.core.types import PressureLedger
from arhpp.meta.diagnostics import build_diagnostics
from arhpp.meta.confidence import (
    ConfidenceInputs, ConfidenceResult, compute_confidence,
)


@dataclass
class DashboardInputs:
    ledger: PressureLedger
    q_pump_gpm: float = 0.0
    q_out_gpm: float = 0.0
    q_effective_gpm: float = 0.0
    q_utube_gpm: float = 0.0
    q_loss_gpm: float = 0.0
    spp_model_psi: float = 0.0
    spp_measured_psi: Optional[float] = None
    bhp_pwd_psi: Optional[float] = None
    pp_ppg: float = 0.0
    fg_ppg: float = 0.0
    mw_ppg: float = 0.0
    kick_severity: str = "none"
    kick_probability: float = 0.0
    loss_class: str = "none"
    losses_fraction: float = 0.0
    ballooning_classification: str = "normal"
    packoff_risk: str = "none"
    packoff_probability: float = 0.0
    washout_risk: str = "none"
    washout_probability: float = 0.0
    nozzle_risk: str = "none"
    nozzle_plugging_pct: float = 0.0
    balling_risk: str = "none"
    balling_probability: float = 0.0
    utube_severity: float = 0.0
    utube_direction: str = "static"
    cuttings_extra_ecd_ppg: float = 0.0
    cuttings_bed_frac: float = 0.0
    gas_bhp_reduction_psi: float = 0.0
    sensor_agreement: float = 1.0
    model_agreement: float = 1.0


@dataclass
class DashboardReport:
    bhp_psi: float = 0.0
    ecd_ppg: float = 0.0
    esd_ppg: float = 0.0
    tvd_ft: float = 0.0
    pp_ppg: float = 0.0
    fg_ppg: float = 0.0
    mw_ppg: float = 0.0
    mw_window_min_ppg: float = 0.0
    mw_window_max_ppg: float = 0.0
    q_pump_gpm: float = 0.0
    q_out_gpm: float = 0.0
    q_effective_gpm: float = 0.0
    q_utube_gpm: float = 0.0
    q_loss_gpm: float = 0.0
    kick_risk: str = "none"
    kick_probability: float = 0.0
    loss_risk: str = "none"
    ballooning: str = "normal"
    packoff_risk: str = "none"
    washout_risk: str = "none"
    nozzle_risk: str = "none"
    balling_risk: str = "none"
    utube_status: str = "static"
    overall_risk: str = "none"
    confidence: ConfidenceResult = field(default_factory=ConfidenceResult)
    diagnostics: object = None
    alerts: List[str] = field(default_factory=list)


def _overall_risk(kick_prob, loss_class, packoff, washout,
                    nozzle, balling, ballooning) -> str:
    if kick_prob >= 0.7 or loss_class in ("severe", "total"):
        return "HIGH"
    if packoff == "high" or washout == "high":
        return "HIGH"
    if (kick_prob >= 0.4 or loss_class == "partial"
            or packoff == "moderate" or washout == "moderate"
            or nozzle in ("moderate", "severe")
            or balling in ("moderate", "high")
            or ballooning == "kick"):
        return "MODERATE"
    if (kick_prob >= 0.2 or loss_class == "seepage"
            or packoff == "low" or washout == "low"
            or nozzle == "minor" or balling == "low"):
        return "LOW"
    return "NONE"


def build_dashboard(inp: DashboardInputs) -> DashboardReport:
    L = inp.ledger
    r = DashboardReport(
        bhp_psi=L.bhp,
        ecd_ppg=L.ecd,
        esd_ppg=(L.hydrostatic_annulus + L.surge - L.swab + L.gas_effect)
                 / max(0.052 * L.tvd_ref, 1e-6),
        tvd_ft=L.tvd_ref,
        pp_ppg=inp.pp_ppg,
        fg_ppg=inp.fg_ppg,
        mw_ppg=inp.mw_ppg,
        q_pump_gpm=inp.q_pump_gpm,
        q_out_gpm=inp.q_out_gpm,
        q_effective_gpm=inp.q_effective_gpm,
        q_utube_gpm=inp.q_utube_gpm,
        q_loss_gpm=inp.q_loss_gpm,
        kick_risk=inp.kick_severity,
        kick_probability=inp.kick_probability,
        loss_risk=inp.loss_class,
        ballooning=inp.ballooning_classification,
        packoff_risk=inp.packoff_risk,
        washout_risk=inp.washout_risk,
        nozzle_risk=inp.nozzle_risk,
        balling_risk=inp.balling_risk,
        utube_status=inp.utube_direction,
    )

    r.mw_window_min_ppg = inp.pp_ppg + 0.3 if inp.pp_ppg > 0 else 0.0
    r.mw_window_max_ppg = (
        max(inp.pp_ppg + 0.3, inp.fg_ppg - 0.3) if inp.fg_ppg > 0 else 0.0)

    r.diagnostics = build_diagnostics(L, spp_psi=inp.spp_model_psi)

    conf_inp = ConfidenceInputs(
        q_pump_gpm=inp.q_pump_gpm,
        q_out_gpm=inp.q_out_gpm,
        q_effective_gpm=inp.q_effective_gpm,
        bhp_model_psi=L.bhp,
        bhp_pwd_psi=inp.bhp_pwd_psi,
        spp_model_psi=inp.spp_model_psi,
        spp_measured_psi=inp.spp_measured_psi,
        sensor_agreement=inp.sensor_agreement,
        model_agreement=inp.model_agreement,
        utube_severity=inp.utube_severity,
        losses_fraction=inp.losses_fraction,
        kick_probability=inp.kick_probability,
        ballooning_present=(inp.ballooning_classification == "ballooning"),
    )
    r.confidence = compute_confidence(conf_inp)

    r.overall_risk = _overall_risk(
        inp.kick_probability, inp.loss_class,
        inp.packoff_risk, inp.washout_risk,
        inp.nozzle_risk, inp.balling_risk,
        inp.ballooning_classification,
    )

    alerts = []
    if inp.kick_probability >= 0.4:
        alerts.append(f"KICK RISK {inp.kick_probability*100:.0f}%")
    if inp.loss_class != "none":
        alerts.append(f"LOSSES: {inp.loss_class}")
    if inp.ballooning_classification == "ballooning":
        alerts.append("BALLOONING detected")
    if inp.packoff_risk not in ("none", "low"):
        alerts.append(f"PACK-OFF: {inp.packoff_risk}")
    if inp.washout_risk not in ("none", "low"):
        alerts.append(f"WASHOUT: {inp.washout_risk}")
    if inp.nozzle_risk not in ("none", "minor"):
        alerts.append(f"NOZZLE PLUG: {inp.nozzle_plugging_pct:.1f}%")
    if inp.balling_risk not in ("none", "low"):
        alerts.append(f"BALLING: {inp.balling_risk}")
    if inp.utube_severity > 0.6:
        alerts.append(
            f"U-TUBE: {inp.utube_direction} "
            f"(sev {inp.utube_severity:.2f})")
    if r.confidence.overall_confidence < 0.5:
        alerts.append(
            f"LOW CONFIDENCE {r.confidence.overall_confidence*100:.0f}%")
    r.alerts = alerts

    return r


def dashboard_to_rows(r: DashboardReport) -> list:
    return [
        {"Item": "BHP (psi)", "Value": round(r.bhp_psi, 2)},
        {"Item": "ECD (ppg)", "Value": round(r.ecd_ppg, 4)},
        {"Item": "ESD (ppg)", "Value": round(r.esd_ppg, 4)},
        {"Item": "TVD (ft)", "Value": round(r.tvd_ft, 1)},
        {"Item": "PP (ppg)", "Value": round(r.pp_ppg, 3)},
        {"Item": "FG (ppg)", "Value": round(r.fg_ppg, 3)},
        {"Item": "MW (ppg)", "Value": round(r.mw_ppg, 3)},
        {"Item": "Q_pump (gpm)", "Value": round(r.q_pump_gpm, 1)},
        {"Item": "Q_out (gpm)", "Value": round(r.q_out_gpm, 1)},
        {"Item": "Q_eff (gpm)", "Value": round(r.q_effective_gpm, 1)},
        {"Item": "Q_utube (gpm)", "Value": round(r.q_utube_gpm, 2)},
        {"Item": "Q_loss (gpm)", "Value": round(r.q_loss_gpm, 2)},
        {"Item": "Kick Risk", "Value": f"{r.kick_risk.upper()} ({r.kick_probability*100:.0f}%)"},
        {"Item": "Loss Risk", "Value": r.loss_risk.upper()},
        {"Item": "Ballooning", "Value": r.ballooning.upper()},
        {"Item": "Pack-Off Risk", "Value": r.packoff_risk.upper()},
        {"Item": "Washout Risk", "Value": r.washout_risk.upper()},
        {"Item": "Nozzle Risk", "Value": r.nozzle_risk.upper()},
        {"Item": "Balling Risk", "Value": r.balling_risk.upper()},
        {"Item": "U-Tube Status", "Value": r.utube_status.upper()},
        {"Item": "Overall Risk", "Value": r.overall_risk},
        {"Item": "Confidence", "Value": f"{r.confidence.overall_confidence*100:.0f}%"},
    ]
