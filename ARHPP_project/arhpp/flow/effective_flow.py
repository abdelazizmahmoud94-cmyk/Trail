"""Effective Flow Engine — reconciles Q_pump, Q_utube, Q_loss, Q_out."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FlowBalance:
    q_pump: float = 0.0
    q_utube: float = 0.0
    q_loss: float = 0.0
    q_out_measured: float = 0.0
    q_out_predicted: float = 0.0
    q_effective_annulus: float = 0.0
    residual_gpm: float = 0.0
    residual_pct: float = 0.0
    is_balanced: bool = False


def reconcile_flow(
    q_pump_gpm: float,
    q_utube_gpm: float,
    q_loss_gpm: float,
    q_out_measured_gpm: Optional[float] = None,
) -> FlowBalance:
    """
    Mass balance:
      Q_eff_annulus = Q_pump + Q_utube - Q_loss
      Q_out_predicted = Q_eff_annulus
    """
    r = FlowBalance(
        q_pump=q_pump_gpm,
        q_utube=q_utube_gpm,
        q_loss=q_loss_gpm,
    )
    r.q_effective_annulus = q_pump_gpm + q_utube_gpm - q_loss_gpm
    r.q_out_predicted = r.q_effective_annulus

    if q_out_measured_gpm is not None:
        r.q_out_measured = q_out_measured_gpm
        r.residual_gpm = r.q_out_measured - r.q_out_predicted
        if q_pump_gpm > 0:
            r.residual_pct = 100.0 * r.residual_gpm / q_pump_gpm
        r.is_balanced = abs(r.residual_pct) < 2.0

    return r
