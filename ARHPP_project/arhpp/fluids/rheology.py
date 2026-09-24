"""Mud Rheology — Bingham, Power Law, Herschel-Bulkley from Fann 6-speed."""

import math
from dataclasses import dataclass

import numpy as np

from arhpp.core.constants import (
    INCH_TO_M, GPM_TO_M3S, FANN_RPM_TO_SR,
)


@dataclass
class Bingham:
    pv: float   # cP
    yp: float   # lbf/100 ft²


@dataclass
class PowerLaw:
    n: float
    k: float    # eq lbf·s^n/100ft²


@dataclass
class HerschelBulkley:
    tau_y: float
    k: float
    n: float


# ═══════════════════════════════════════════════════════════════
#  Fit all three models from Fann 6-speed
# ═══════════════════════════════════════════════════════════════

def from_fann_6(t600, t300, t200, t100, t6, t3) -> dict:
    """Fit Bingham, Power Law, HB from Fann 6-speed readings."""
    # Bingham
    pv = t600 - t300
    yp = t300 - pv
    bingham = Bingham(pv=pv, yp=yp)

    # Power Law
    if t300 > 0 and t600 > 0:
        n_pl = 3.32 * math.log10(t600 / t300)
    else:
        n_pl = 1.0
    if n_pl > 0:
        k_pl = t300 / (511.0 ** n_pl)
    else:
        k_pl = 0.0
    pl = PowerLaw(n=n_pl, k=k_pl)

    # Herschel-Bulkley (curve_fit)
    rpms = np.array([600., 300., 200., 100., 6., 3.])
    taus = np.array([t600, t300, t200, t100, t6, t3], dtype=float)
    gammas = rpms * FANN_RPM_TO_SR

    try:
        from scipy.optimize import curve_fit

        def hb(g, ty, K, n):
            return ty + K * np.power(g, n)

        p0 = [max(0.0, yp), max(1e-3, k_pl), max(0.1, n_pl)]
        bounds = ([0.0, 1e-6, 0.05], [200.0, 500.0, 2.0])
        popt, _ = curve_fit(hb, gammas, taus, p0=p0,
                             bounds=bounds, maxfev=20000)
        hb_model = HerschelBulkley(tau_y=float(popt[0]),
                                     k=float(popt[1]),
                                     n=float(popt[2]))
    except Exception:
        hb_model = HerschelBulkley(tau_y=yp, k=k_pl, n=n_pl)

    return {
        "bingham": bingham,
        "power_law": pl,
        "herschel_bulkley": hb_model,
    }


# ═══════════════════════════════════════════════════════════════
#  Wall Shear Rate (HB, per API RP 13D)
# ═══════════════════════════════════════════════════════════════

def wall_shear_rate_pipe(q_gpm: float, d_in: float, n: float) -> float:
    """
    Wall shear rate for HB fluid in pipe.

    gamma_w = [(3n+1)/(4n)] * [8V/d]
    Returns 1/s (SI).
    """
    if q_gpm <= 0 or d_in <= 0 or n <= 0:
        return 0.0
    d_m = d_in * INCH_TO_M
    area_m2 = math.pi * (d_m / 2.0) ** 2
    V_ms = (q_gpm * GPM_TO_M3S) / area_m2
    return ((3.0 * n + 1.0) / (4.0 * n)) * (8.0 * V_ms / d_m)


def wall_shear_rate_annulus(q_gpm: float, dh_in: float,
                              dp_in: float, n: float) -> float:
    """
    Wall shear rate for HB fluid in annulus (slot approximation).

    gamma_w = [(2n+1)/(3n)] * [12V / Dh_eq]
    where Dh_eq = Dh - Dp (hydraulic diameter = 2*clearance)
    """
    if q_gpm <= 0 or dh_in <= dp_in or n <= 0:
        return 0.0
    dh_m = dh_in * INCH_TO_M
    dp_m = dp_in * INCH_TO_M
    gap_m = dh_m - dp_m
    if gap_m <= 0:
        return 0.0
    area_m2 = math.pi / 4.0 * (dh_m ** 2 - dp_m ** 2)
    V_ms = (q_gpm * GPM_TO_M3S) / area_m2
    return ((2.0 * n + 1.0) / (3.0 * n)) * (12.0 * V_ms / gap_m)


def apparent_viscosity(tau_w_pa: float, gamma_w_1s: float) -> float:
    """Apparent viscosity in cP."""
    if gamma_w_1s <= 0:
        return 0.0
    return (tau_w_pa / gamma_w_1s) * 1000.0
