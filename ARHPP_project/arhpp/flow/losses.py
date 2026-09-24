"""Losses Engine — seepage/partial/severe/total + Q_effective correction."""

from dataclasses import dataclass
from typing import Optional

from arhpp.core.constants import (
    LOSS_SEEPAGE_MAX, LOSS_PARTIAL_MAX, LOSS_SEVERE_MAX,
    PSI_PER_FT_PER_PPG,
)
from arhpp.calibration.context import get_param


@dataclass
class LossResult:
    q_pump: float = 0.0
    q_out_measured: float = 0.0
    q_loss_gpm: float = 0.0
    loss_fraction: float = 0.0
    loss_class: str = "none"
    bhp_reduction_psi: float = 0.0
    ecd_reduction_ppg: float = 0.0
    is_active: bool = False


def classify_loss(fraction: float) -> str:
    """Loss classification — reads thresholds from context."""
    if fraction <= 0:
        return "none"

    seepage_max = get_param("loss_seepage_max", default=LOSS_SEEPAGE_MAX)
    partial_max = get_param("loss_partial_max", default=LOSS_PARTIAL_MAX)
    severe_max = get_param("loss_severe_max", default=LOSS_SEVERE_MAX)

    if fraction <= seepage_max:
        return "seepage"
    if fraction <= partial_max:
        return "partial"
    if fraction <= severe_max:
        return "severe"
    return "total"


def compute_losses(
    q_pump_gpm: float,
    q_out_gpm: float,
    *,
    mw_ppg: float,
    tvd_ft: float,
    annular_fp_psi: float,
    loss_depth_ft: Optional[float] = None,
) -> LossResult:
    """
    Physical effects of losses:

      1. Friction LOSS below loss zone:
         dPf = annular_fp * (1 - (Q_eff/Q_pump)^2)

      2. Hydrostatic column LOSS above loss zone:
         dPh = 0.052 * MW * (TVD - TVD_loss)
         (The fluid is lost -> column is shorter)
    """
    r = LossResult(q_pump=q_pump_gpm, q_out_measured=q_out_gpm)

    if q_pump_gpm <= 0:
        return r

    q_loss = max(0.0, q_pump_gpm - q_out_gpm)
    r.q_loss_gpm = q_loss
    r.loss_fraction = q_loss / q_pump_gpm
    r.loss_class = classify_loss(r.loss_fraction)
    r.is_active = r.loss_fraction > 0.0

    if not r.is_active or tvd_ft <= 0:
        return r

    if loss_depth_ft is None:
        loss_depth_ft = tvd_ft * 0.8

    # Friction share
    q_ratio_below = 1.0 - r.loss_fraction
    dp_friction_below = annular_fp_psi * (1.0 - q_ratio_below ** 2)

    # Hydrostatic share
    dp_hydrostatic = (PSI_PER_FT_PER_PPG * mw_ppg
                       * r.loss_fraction * loss_depth_ft / 2)

    r.bhp_reduction_psi = dp_friction_below + dp_hydrostatic
    r.ecd_reduction_ppg = r.bhp_reduction_psi / (0.052 * tvd_ft)
    return r
