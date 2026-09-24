"""Hybrid Pore Pressure — Corrected Eaton equations."""

from dataclasses import dataclass, field
from typing import List

from arhpp.calibration.context import get_param
from arhpp.core.constants import MW_NORMAL_PPG, OBG_DEFAULT_PPG
from arhpp.pore_pressure.nct import NCTFit, evaluate_nct
from arhpp.pore_pressure.gas_models import gas_score_at_tvd


@dataclass
class PPComponent:
    tvd_ft: float = 0.0
    pp_mech_dc: float = 0.0
    pp_mech_sigma: float = 0.0
    pp_gas: float = 0.0
    pp_temp: float = 0.0
    pp_field: float = 0.0
    pp_hybrid: float = 0.0
    obg_ppg: float = 0.0
    weights: dict = field(default_factory=dict)


def overburden_gradient_ppg(tvd_ft: float,
                              obg_shallow: float = None,
                              obg_deep: float = None,
                              transition_tvd: float = None) -> float:
    if obg_shallow is None:
        obg_shallow = get_param("obg_shallow", default=14.0)
    if obg_deep is None:
        obg_deep = get_param("obg_deep", default=OBG_DEFAULT_PPG)
    if transition_tvd is None:
        transition_tvd = get_param("transition_tvd", default=8000.0)
    if tvd_ft <= 0:
        return obg_shallow
    f = min(1.0, tvd_ft / max(transition_tvd, 1.0))
    return obg_shallow + (obg_deep - obg_shallow) * f


def pp_from_dc_eaton(dc_actual: float, dc_nct: float, obg: float,
                       pp_normal: float = None,
                       eaton_exp: float = None) -> float:
    """
    Eaton from d-exponent (CORRECTED):
      PP = OBG - (OBG - PP_normal) * (dc_actual / dc_nct)^eaton_exp
    """
    if pp_normal is None:
        pp_normal = get_param("mw_normal_ppg", default=MW_NORMAL_PPG)
    if eaton_exp is None:
        eaton_exp = get_param("eaton_exp_dc", default=1.2)
    if dc_actual <= 0 or dc_nct <= 0 or obg <= pp_normal:
        return pp_normal
    ratio = dc_actual / dc_nct
    delta = (obg - pp_normal) * (ratio ** eaton_exp)
    pp = obg - delta
    return max(pp_normal * 0.5, min(pp, obg * 0.95))


def pp_from_sigma_eaton(sg_actual: float, sg_nct: float, obg: float,
                          pp_normal: float = None,
                          eaton_exp: float = None) -> float:
    """
    Eaton from sigma (CORRECTED):
      PP = OBG - (OBG - PP_normal) * (sigma_actual / sigma_nct)^eaton_exp
    """
    if pp_normal is None:
        pp_normal = get_param("mw_normal_ppg", default=MW_NORMAL_PPG)
    if eaton_exp is None:
        eaton_exp = get_param("eaton_exp_sigma", default=1.0)
    if sg_actual <= 0 or sg_nct <= 0 or obg <= pp_normal:
        return pp_normal
    ratio = sg_actual / sg_nct
    delta = (obg - pp_normal) * (ratio ** eaton_exp)
    pp = obg - delta
    return max(pp_normal * 0.5, min(pp, obg * 0.95))


def pp_from_gas_score(score: float, pp_normal: float = None,
                        max_lift: float = 3.0) -> float:
    if pp_normal is None:
        pp_normal = get_param("mw_normal_ppg", default=MW_NORMAL_PPG)
    return pp_normal + max(0.0, min(1.0, score)) * max_lift


def pp_from_temperature(tvd_ft: float, temp_f: float,
                          t_surface_f: float = None,
                          grad: float = None) -> float:
    if t_surface_f is None:
        t_surface_f = get_param("t_surface_f", default=90.0)
    if grad is None:
        grad = get_param("gradient_normal_f_per_ft", default=0.015)
    if tvd_ft <= 0:
        return 0.0
    exp = t_surface_f + grad * tvd_ft
    anomaly = temp_f - exp
    return max(0.0, anomaly / 30.0)


def inclination_factor_pp(inclination_deg: float) -> float:
    coeff = get_param("inclination_pp_coeff", default=0.002)
    return 1.0 + coeff * abs(inclination_deg)


def compute_hybrid_pp(
    tvd_ft: float,
    dc_actual: float,
    dc_nct: float,
    sigma_actual: float,
    sigma_nct: float,
    gas_score: float,
    temp_f: float,
    pp_field_ppg: float,
    weights: dict = None,
    t_surface_f: float = None,
    grad_normal_f_per_ft: float = None,
    inclination_deg: float = 0.0,
) -> PPComponent:
    if weights is None:
        weights = {
            "dc":    get_param("w_dc", default=0.40),
            "sigma": get_param("w_sigma", default=0.20),
            "gas":   get_param("w_gas", default=0.15),
            "temp":  get_param("w_temp", default=0.10),
            "field": get_param("w_field", default=0.15),
        }

    total_w = sum(weights.values()) or 1.0
    obg = overburden_gradient_ppg(tvd_ft)

    pp_dc = pp_from_dc_eaton(dc_actual, dc_nct, obg)
    pp_sg = pp_from_sigma_eaton(sigma_actual, sigma_nct, obg)
    pp_gs = pp_from_gas_score(gas_score)
    pp_t = get_param("mw_normal_ppg", default=MW_NORMAL_PPG) + \
           pp_from_temperature(tvd_ft, temp_f, t_surface_f,
                                 grad_normal_f_per_ft)
    pp_fl = pp_field_ppg if pp_field_ppg > 0 else \
            get_param("mw_normal_ppg", default=MW_NORMAL_PPG)

    pp_h = (
        weights["dc"] * pp_dc
        + weights["sigma"] * pp_sg
        + weights["gas"] * pp_gs
        + weights["temp"] * pp_t
        + weights["field"] * pp_fl
    ) / total_w

    pp_h *= inclination_factor_pp(inclination_deg)

    return PPComponent(
        tvd_ft=tvd_ft,
        pp_mech_dc=pp_dc,
        pp_mech_sigma=pp_sg,
        pp_gas=pp_gs,
        pp_temp=pp_t,
        pp_field=pp_fl,
        pp_hybrid=pp_h,
        obg_ppg=obg,
        weights=weights,
    )


def build_pp_profile(tvds: List[float],
                       dc_actual: List[float],
                       sigma_actual: List[float],
                       temps_f: List[float],
                       field_pp_ppg: List[float],
                       nct_dc: NCTFit,
                       nct_sigma: NCTFit,
                       gas_indicators,
                       weights: dict = None) -> List[PPComponent]:
    out = []
    for i, tvd in enumerate(tvds):
        dc_nct = evaluate_nct(nct_dc, tvd)
        sg_nct = evaluate_nct(nct_sigma, tvd)
        gas_s = gas_score_at_tvd(gas_indicators, tvd)
        out.append(compute_hybrid_pp(
            tvd_ft=tvd,
            dc_actual=dc_actual[i],
            dc_nct=dc_nct,
            sigma_actual=sigma_actual[i],
            sigma_nct=sg_nct,
            gas_score=gas_s,
            temp_f=temps_f[i],
            pp_field_ppg=field_pp_ppg[i],
            weights=weights,
        ))
    return out
