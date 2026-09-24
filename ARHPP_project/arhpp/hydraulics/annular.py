"""Annular Hydraulics Engine — HB + Haciislamoglu eccentricity + RPM."""

import math
from dataclasses import dataclass
from typing import List

from arhpp.core.constants import (
    PPG_TO_KG_M3, INCH_TO_M, FT_TO_M, GPM_TO_M3S,
    LBF_100FT2_TO_PA, PA_TO_PSI, RE_LAMINAR_MAX,
)
from arhpp.geometry.well_geometry import effective_hole_id
from arhpp.geometry.bha import string_od_at_md
from arhpp.hydraulics.pipe import _dodge_metzner, _colebrook_friction
from arhpp.calibration.context import get_param


@dataclass
class AnnularSectionResult:
    top_md: float = 0.0
    bottom_md: float = 0.0
    length_ft: float = 0.0
    hole_id_in: float = 0.0
    pipe_od_in: float = 0.0
    fluid_id: str = ""
    mw_ppg: float = 0.0
    velocity_fps: float = 0.0
    shear_rate_wall: float = 0.0
    tau_wall_pa: float = 0.0
    re_generalized: float = 0.0
    flow_regime: str = "static"
    f_concentric: float = 0.0
    ecc_correction: float = 1.0
    rpm_correction: float = 1.0
    dp_psi: float = 0.0


def eccentricity_correction(n: float, dp_ratio: float, e: float) -> float:
    """
    Haciislamoglu & Cartalos (1994) laminar eccentricity correction.

    dp_ratio = D_pipe / D_hole
    e = eccentricity (0-1)

    Reads coefficients from calibration context (defaults match paper).
    """
    if dp_ratio <= 0 or dp_ratio >= 1.0:
        return 1.0
    if n <= 0:
        n = 1.0
    a = get_param("ecc_a", default=0.072)
    b = get_param("ecc_b", default=1.500)
    c = get_param("ecc_c", default=0.960)
    sq = math.sqrt(n)
    r = (
        1.0
        - a * (e / n) * (dp_ratio ** 0.8454)
        - b * e * e * sq * (dp_ratio ** 0.1852)
        + c * e ** 3 * sq * (dp_ratio ** 0.2527)
    )
    return max(0.2, min(1.0, r))


def rpm_correction(rpm: float, coeff: float = None) -> float:
    """
    RPM effect on annular friction.

    Physical basis:
      Rotation creates Taylor vortices in the annulus which
      increase wall shear stress. Coefficient scales with sqrt(RPM).

    Reference:
      Ahmed & Miska (2000) — "Experimental Study of Annular
      Friction with Pipe Rotation"

    Empirical range for coefficient: 0.05 to 0.15
    Default 0.10 is conservative.
    """
    if rpm <= 0:
        return 1.0
    if coeff is None:
        coeff = get_param("rpm_coeff", default=0.10)
    return 1.0 + coeff * math.sqrt(rpm / 100.0)


def annular_section_friction(
    q_gpm: float,
    hole_id_in: float,
    pipe_od_in: float,
    length_ft: float,
    mw_ppg: float,
    tau_y_field: float,
    k_field: float,
    n: float,
    eccentricity: float = 0.5,
    rpm: float = 0.0,
) -> AnnularSectionResult:
    """HB friction in an annular section (slot approximation)."""
    r = AnnularSectionResult(
        length_ft=length_ft, hole_id_in=hole_id_in,
        pipe_od_in=pipe_od_in, mw_ppg=mw_ppg,
    )
    gap_in = hole_id_in - pipe_od_in
    if gap_in <= 0 or length_ft <= 0 or q_gpm <= 0 or n <= 0:
        return r

    dh_m = hole_id_in * INCH_TO_M
    dp_m = pipe_od_in * INCH_TO_M
    gap_m = gap_in * INCH_TO_M
    L_m = length_ft * FT_TO_M

    rho = mw_ppg * PPG_TO_KG_M3
    tau_y = tau_y_field * LBF_100FT2_TO_PA
    K = k_field * LBF_100FT2_TO_PA

    area = math.pi / 4.0 * (dh_m ** 2 - dp_m ** 2)
    if area <= 0:
        return r
    V = (q_gpm * GPM_TO_M3S) / area
    V_fps = V / FT_TO_M

    gamma_w = (2.0 * n + 1.0) / (3.0 * n) * (12.0 * V / gap_m)
    tau_w = tau_y + K * gamma_w ** n

    # Generalized Reynolds (slot form)
    if K > 0 and V > 0:
        Re_g = (rho * V ** (2.0 - n) * gap_m ** n) / (
            K * ((2.0 * n + 1.0) / (3.0 * n)) ** n * 12.0 ** (n - 1.0)
        )
    else:
        Re_g = 0.0

    # Concentric friction
    if Re_g < RE_LAMINAR_MAX:
        dp_pa_conc = 4.0 * tau_w * L_m / gap_m
        f_c = 0.0
        regime = "laminar"
    else:
        eps_d = 0.0018 * INCH_TO_M / gap_m
        f_c = _colebrook_friction(max(Re_g, 1.0), eps_d, n)
        if f_c <= 0:
            f_c = _dodge_metzner(max(Re_g, 1.0), n)
        dp_pa_conc = 2.0 * f_c * rho * V * V * L_m / gap_m
        regime = "turbulent"

    # Corrections
    if regime == "laminar":
        ecc = eccentricity_correction(
            n, pipe_od_in / hole_id_in, eccentricity)
    else:
        ecc = 1.0
    rpmc = rpm_correction(rpm)

    dp_pa = dp_pa_conc * ecc * rpmc

    r.velocity_fps = V_fps
    r.shear_rate_wall = gamma_w
    r.tau_wall_pa = tau_w
    r.re_generalized = Re_g
    r.flow_regime = regime
    r.f_concentric = f_c
    r.ecc_correction = ecc
    r.rpm_correction = rpmc
    r.dp_psi = dp_pa * PA_TO_PSI
    return r


def annular_friction_total(
    q_gpm: float,
    hole_sections: List,
    bha_sections: List,
    annulus_col,
    eccentricity: float = 0.5,
    rpm: float = 0.0,
    step_ft: float = 30.0,
) -> dict:
    total = 0.0
    results: List[AnnularSectionResult] = []

    if not annulus_col.segments:
        return {"dp_total_psi": 0.0, "sections": []}

    for seg in annulus_col.segments:
        md = seg.top_md
        bot = seg.bottom_md
        while md < bot:
            nxt = min(md + step_ft, bot)
            mid = 0.5 * (md + nxt)
            hid = effective_hole_id(hole_sections, mid)
            od = string_od_at_md(bha_sections, mid)
            if hid > od > 0:
                r = annular_section_friction(
                    q_gpm=q_gpm,
                    hole_id_in=hid,
                    pipe_od_in=od,
                    length_ft=nxt - md,
                    mw_ppg=seg.mw,
                    tau_y_field=seg.tau_y,
                    k_field=seg.k,
                    n=seg.n,
                    eccentricity=eccentricity,
                    rpm=rpm,
                )
                r.top_md = md
                r.bottom_md = nxt
                r.fluid_id = seg.fluid_id
                total += r.dp_psi
                results.append(r)
            md = nxt

    return {"dp_total_psi": total, "sections": results}
