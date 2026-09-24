"""Nozzle Plug Engine — compare expected vs actual bit dP."""

from dataclasses import dataclass
from arhpp.core.constants import (
    NOZZLE_PLUG_MIN_FRAC, NOZZLE_PLUG_SEVERE_FRAC,
)


@dataclass
class NozzlePlugResult:
    tfa_expected_in2: float = 0.0
    tfa_effective_in2: float = 0.0
    plugging_fraction: float = 0.0
    plugging_percent: float = 0.0
    risk: str = "none"
    expected_dp_psi: float = 0.0
    actual_dp_psi: float = 0.0
    is_flagged: bool = False


def compute_nozzle_plug(expected_dp_psi: float, actual_dp_psi: float,
                          q_gpm: float, mw_ppg: float,
                          tfa_expected_in2: float,
                          cd: float = 0.95) -> NozzlePlugResult:
    """
    TFA_eff = Q * sqrt(MW / (12032 * Cd^2 * dP_actual))
    plugging = 1 - TFA_eff / TFA_expected
    """
    r = NozzlePlugResult(
        tfa_expected_in2=tfa_expected_in2,
        expected_dp_psi=expected_dp_psi,
        actual_dp_psi=actual_dp_psi)
    if q_gpm <= 0 or mw_ppg <= 0 or actual_dp_psi <= 0 or tfa_expected_in2 <= 0:
        return r
    sq = (mw_ppg * q_gpm * q_gpm) / (
        12032.0 * cd * cd * actual_dp_psi)
    if sq <= 0:
        return r
    r.tfa_effective_in2 = sq ** 0.5
    r.plugging_fraction = max(
        0.0, 1.0 - r.tfa_effective_in2 / tfa_expected_in2)
    r.plugging_percent = 100.0 * r.plugging_fraction

    if r.plugging_fraction < NOZZLE_PLUG_MIN_FRAC:
        r.risk = "none"
    elif r.plugging_fraction < 0.20:
        r.risk = "minor"
    elif r.plugging_fraction < NOZZLE_PLUG_SEVERE_FRAC:
        r.risk = "moderate"
    else:
        r.risk = "severe"
    r.is_flagged = r.plugging_fraction >= NOZZLE_PLUG_MIN_FRAC
    return r
