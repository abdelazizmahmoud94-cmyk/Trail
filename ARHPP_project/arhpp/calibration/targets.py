"""Calibration targets — what we compare against."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class WellTarget:
    well_id: str
    e_bhp_psi: float = 0.0
    e_bhp_norm: float = 0.0
    e_ecd_ppg: float = 0.0
    e_ecd_norm: float = 0.0
    e_spp_psi: float = 0.0
    e_spp_norm: float = 0.0
    e_pp_ppg: float = 0.0
    e_pp_norm: float = 0.0
    e_kick: float = 0.0
    e_loss: float = 0.0
    composite: float = 0.0
    has_pwd: bool = False
    has_spp: bool = False
    has_pp: bool = False
    n_objectives: int = 0


DEFAULT_WEIGHTS = {
    "bhp": 0.35,
    "ecd": 0.25,
    "spp": 0.20,
    "pp": 0.15,
    "kick": 0.05,
    "loss": 0.05,
}


def normalized_error(pred: float, obs: float, scale: float) -> float:
    if scale <= 1e-9:
        return 0.0
    return abs(pred - obs) / scale


def compute_well_target(well,
                          pred_bhp: float,
                          pred_ecd: float,
                          pred_spp: float,
                          pred_pp: float,
                          pred_kick_severity: str,
                          pred_loss_class: str,
                          weights: dict = None) -> WellTarget:
    w = weights or DEFAULT_WEIGHTS
    t = WellTarget(well_id=well.well_id)

    if well.pwd_bhp_psi is not None and well.pwd_bhp_psi > 0:
        t.e_bhp_psi = pred_bhp - well.pwd_bhp_psi
        t.e_bhp_norm = normalized_error(pred_bhp, well.pwd_bhp_psi, 500.0)
        t.has_pwd = True

    if well.pwd_ecd_ppg is not None and well.pwd_ecd_ppg > 0:
        t.e_ecd_ppg = pred_ecd - well.pwd_ecd_ppg
        t.e_ecd_norm = normalized_error(pred_ecd, well.pwd_ecd_ppg, 0.3)
        t.has_pwd = True

    if well.spp_measured_psi is not None and well.spp_measured_psi > 0:
        t.e_spp_psi = pred_spp - well.spp_measured_psi
        t.e_spp_norm = normalized_error(pred_spp, well.spp_measured_psi, 300.0)
        t.has_spp = True

    if well.pp_reference_ppg is not None and well.pp_reference_ppg > 0:
        t.e_pp_ppg = pred_pp - well.pp_reference_ppg
        t.e_pp_norm = normalized_error(pred_pp, well.pp_reference_ppg, 1.0)
        t.has_pp = True

    pred_kick = pred_kick_severity in ("severe", "blowout-risk", "moderate")
    if pred_kick != well.had_kick:
        t.e_kick = 1.0
    pred_loss = pred_loss_class not in ("none",)
    if pred_loss != well.had_losses:
        t.e_loss = 1.0

    num = 0.0
    den = 0.0
    if t.has_pwd:
        num += w["bhp"] * t.e_bhp_norm + w["ecd"] * t.e_ecd_norm
        den += w["bhp"] + w["ecd"]
    if t.has_spp:
        num += w["spp"] * t.e_spp_norm
        den += w["spp"]
    if t.has_pp:
        num += w["pp"] * t.e_pp_norm
        den += w["pp"]
    num += w["kick"] * t.e_kick + w["loss"] * t.e_loss
    den += w["kick"] + w["loss"]

    t.composite = num / den if den > 0 else 0.0
    t.n_objectives = int(t.has_pwd) + int(t.has_spp) + int(t.has_pp)
    return t
