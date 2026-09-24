"""Mud Physics — P/T corrections on density and rheology."""

from arhpp.core.constants import (
    T_REF_F, P_REF_PSI,
    K_TEMP_FACTOR_DEFAULT, TAU_Y_TEMP_FACTOR_DEFAULT,
    LBF_100FT2_TO_PA, INCH_TO_M, PA_TO_PSI,
)
from arhpp.calibration.context import get_param


def mw_corrected(mw_ref: float, p_psi: float, t_f: float,
                 compressibility=None, thermal_exp=None) -> float:
    """
    rho(P,T) = rho0 * (1 + c*dP) * (1 - alpha*dT)
    """
    if compressibility is None:
        compressibility = get_param("mw_compressibility", default=3.0e-6)
    if thermal_exp is None:
        thermal_exp = get_param("mw_thermal_expansion", default=2.5e-4)
    dp = p_psi - P_REF_PSI
    dt = t_f - T_REF_F
    return mw_ref * (1.0 + compressibility * dp) * (1.0 - thermal_exp * dt)


def mw_with_gas_cut(mw_base: float, gas_cut: float) -> float:
    return mw_base * (1.0 - gas_cut)


def pv_yp_temperature(pv_ref: float, yp_ref: float, t_f: float,
                       t_ref_f: float = 100.0,
                       pv_slope: float = 0.005,
                       yp_slope: float = 0.010):
    dt = t_f - t_ref_f
    return pv_ref * (1 + pv_slope * dt), yp_ref * (1 + yp_slope * dt)


# ═══════════════════════════════════════════════════════════════
#  Temperature correction (reads from calibration context)
# ═══════════════════════════════════════════════════════════════

def K_temperature_corrected(k_ref: float, k_factor=None) -> float:
    """K at downhole T = K_ref * factor."""
    if k_factor is None:
        k_factor = get_param("k_temp_factor",
                             default=K_TEMP_FACTOR_DEFAULT)
    return k_ref * k_factor


def tau_y_temperature_corrected(tau_y_ref: float, tau_y_factor=None) -> float:
    """tau_y at downhole T = tau_y_ref * factor."""
    if tau_y_factor is None:
        tau_y_factor = get_param("tau_y_temp_factor",
                                 default=TAU_Y_TEMP_FACTOR_DEFAULT)
    return tau_y_ref * tau_y_factor


# ═══════════════════════════════════════════════════════════════
#  Gel strengths
# ═══════════════════════════════════════════════════════════════

def gel_break_gradient_psi_ft(gel_strength_lbf100: float,
                                gap_in: float) -> float:
    """
    Minimum pressure gradient to break gel in annular slot.

    dP/dL = 2 * tau_gel / h   [Pa/m -> psi/ft]
    """
    if gap_in <= 0:
        return 0.0
    tau_gel_pa = gel_strength_lbf100 * LBF_100FT2_TO_PA
    gap_m = gap_in * INCH_TO_M
    dpdl_pa_per_m = 2.0 * tau_gel_pa / gap_m
    return dpdl_pa_per_m * 0.00014813


def gel_break_pressure_psi(gel_strength_lbf100: float,
                            gap_in: float,
                            length_ft: float) -> float:
    return gel_break_gradient_psi_ft(
        gel_strength_lbf100, gap_in) * length_ft


def apply_temp_correction_to_segment(seg, k_factor=None,
                                       tau_y_factor=None) -> None:
    """Apply T-correction to segment's k and tau_y in-place."""
    seg.k = K_temperature_corrected(seg.k, k_factor)
    seg.tau_y = tau_y_temperature_corrected(seg.tau_y, tau_y_factor)
