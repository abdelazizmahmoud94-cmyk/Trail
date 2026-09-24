"""Pipe Hydraulics Engine — HB friction with Colebrook turbulent."""

import math
from dataclasses import dataclass
from typing import List

from arhpp.core.constants import (
    PPG_TO_KG_M3, INCH_TO_M, FT_TO_M, GPM_TO_M3S,
    LBF_100FT2_TO_PA, PA_TO_PSI, RE_LAMINAR_MAX, RE_TURBULENT_MIN,
    PIPE_ROUGHNESS_IN_DEFAULT,
)


@dataclass
class PipeSectionResult:
    top_md: float = 0.0
    bottom_md: float = 0.0
    length_ft: float = 0.0
    id_in: float = 0.0
    fluid_id: str = ""
    mw_ppg: float = 0.0
    velocity_fps: float = 0.0
    shear_rate_wall: float = 0.0
    tau_wall_pa: float = 0.0
    re_generalized: float = 0.0
    flow_regime: str = "static"
    friction_factor: float = 0.0
    dp_psi: float = 0.0


def _dodge_metzner(Re_g: float, n: float, tol: float = 1e-7) -> float:
    """Iterative Dodge-Metzner for power-law turbulent flow."""
    if n <= 0 or Re_g <= 0:
        return 0.0
    f = 0.01
    for _ in range(60):
        arg = Re_g * f ** (1.0 - n / 2.0)
        if arg <= 0:
            break
        rhs = (4.0 / n ** 0.75) * math.log10(arg) - 0.4 / n ** 1.2
        if rhs <= 0:
            f *= 2.0
            continue
        f_new = 1.0 / (rhs * rhs)
        if abs(f_new - f) < tol:
            return f_new
        f = 0.5 * (f + f_new)
    return f


def _colebrook_friction(Re: float, eps_d: float, n: float) -> float:
    """
    Colebrook-White for turbulent flow (iterative).
    f = 1 / [-2 * log10(eps/(3.7*D) + 2.51/(Re*sqrt(f)))]^2

    For n != 1 we blend with Dodge-Metzner.
    """
    if Re < 1.0 or eps_d < 0:
        return 0.0
    # Swamee-Jain explicit initial guess
    try:
        f = 0.25 / (math.log10(eps_d / 3.7 + 5.74 / (Re ** 0.9))) ** 2
    except (ValueError, ZeroDivisionError):
        return _dodge_metzner(Re, n)
    if f <= 0:
        return _dodge_metzner(Re, n)
    # Newton refinement
    for _ in range(12):
        try:
            rhs = -2.0 * math.log10(eps_d / 3.7 + 2.51 / (Re * math.sqrt(f)))
        except (ValueError, ZeroDivisionError):
            return _dodge_metzner(Re, n)
        if abs(rhs) < 1e-9:
            break
        f_new = 1.0 / (rhs * rhs)
        if abs(f_new - f) < 1e-6:
            return f_new
        f = f_new
    return f


def _interpolate_transition(Re: float, f_lam: float, f_turb: float) -> float:
    """Smooth transition between laminar and turbulent (log interpolation)."""
    Re_lo, Re_hi = RE_LAMINAR_MAX, RE_TURBULENT_MIN
    if Re <= Re_lo:
        return f_lam
    if Re >= Re_hi:
        return f_turb
    x = (math.log10(Re) - math.log10(Re_lo)) / (
        math.log10(Re_hi) - math.log10(Re_lo))
    return f_lam * (1 - x) + f_turb * x


def pipe_section_friction(q_gpm: float, d_in: float,
                            length_ft: float, mw_ppg: float,
                            tau_y_field: float, k_field: float, n: float,
                            roughness_in: float = PIPE_ROUGHNESS_IN_DEFAULT
                            ) -> PipeSectionResult:
    """HB friction in a single pipe section, SI-internal."""
    r = PipeSectionResult(
        length_ft=length_ft, id_in=d_in, mw_ppg=mw_ppg,
    )
    d_m = d_in * INCH_TO_M
    L_m = length_ft * FT_TO_M

    if d_m <= 0 or L_m <= 0 or q_gpm <= 0 or n <= 0:
        return r

    rho = mw_ppg * PPG_TO_KG_M3
    tau_y = tau_y_field * LBF_100FT2_TO_PA
    K = k_field * LBF_100FT2_TO_PA

    area = math.pi * (d_m / 2.0) ** 2
    V = (q_gpm * GPM_TO_M3S) / area
    V_fps = V / FT_TO_M

    gamma_w = (3.0 * n + 1.0) / (4.0 * n) * (8.0 * V / d_m)
    tau_w = tau_y + K * gamma_w ** n

    # Metzner-Reed generalized Reynolds
    if K > 0 and V > 0:
        Re_g = (rho * V ** (2.0 - n) * d_m ** n) / (
            K * ((3.0 * n + 1.0) / (4.0 * n)) ** n * 8.0 ** (n - 1.0)
        )
    else:
        Re_g = 0.0

    if Re_g < 1.0:
        dp_pa = 4.0 * tau_w * L_m / d_m
        f = 0.0
        regime = "laminar"
    else:
        dp_laminar = 4.0 * tau_w * L_m / d_m
        f_laminar = 64.0 / Re_g if Re_g > 0 else 0.0

        eps_d = roughness_in * INCH_TO_M / d_m
        f_turb = _colebrook_friction(max(Re_g, 1.0), eps_d, n)
        if f_turb <= 0:
            f_turb = _dodge_metzner(max(Re_g, 1.0), n)

        f_eff = _interpolate_transition(Re_g, f_laminar, f_turb)

        if Re_g < RE_LAMINAR_MAX:
            dp_pa = dp_laminar
            regime = "laminar"
        elif Re_g > RE_TURBULENT_MIN:
            dp_pa = 2.0 * f_turb * rho * V * V * L_m / d_m
            regime = "turbulent"
        else:
            dp_turb = 2.0 * f_turb * rho * V * V * L_m / d_m
            w = (Re_g - RE_LAMINAR_MAX) / (
                RE_TURBULENT_MIN - RE_LAMINAR_MAX)
            dp_pa = (1 - w) * dp_laminar + w * dp_turb
            regime = "transition"
        f = f_eff

    r.velocity_fps = V_fps
    r.shear_rate_wall = gamma_w
    r.tau_wall_pa = tau_w
    r.re_generalized = Re_g
    r.flow_regime = regime
    r.friction_factor = f
    r.dp_psi = dp_pa * PA_TO_PSI
    return r


def pipe_friction_total(q_gpm: float, bha_sections: List,
                          string_col) -> dict:
    """Integrate pipe friction over the string."""
    total = 0.0
    results: List[PipeSectionResult] = []

    for seg in string_col.segments:
        for sec in bha_sections:
            top = max(seg.top_md, sec.top_md)
            bot = min(seg.bottom_md, sec.bottom_md)
            if bot - top <= 0 or sec.id_in <= 0:
                continue
            r = pipe_section_friction(
                q_gpm=q_gpm,
                d_in=sec.id_in,
                length_ft=bot - top,
                mw_ppg=seg.mw,
                tau_y_field=seg.tau_y,
                k_field=seg.k,
                n=seg.n,
            )
            r.top_md = top
            r.bottom_md = bot
            r.fluid_id = seg.fluid_id
            total += r.dp_psi
            results.append(r)

    return {"dp_total_psi": total, "sections": results}
