"""Gas Behaviour Engine — PVT, expansion, migration, BHP effect."""

import math
from dataclasses import dataclass, field
from typing import List

from arhpp.core.constants import (
    PSI_PER_FT_PER_PPG, GAS_SG_DEFAULT,
    GAS_SOLUBILITY_OBM_DEFAULT, GAS_BUBBLE_RISE_FPS,
)
from arhpp.calibration.context import get_param


@dataclass
class GasSectionResult:
    top_md: float = 0.0
    bottom_md: float = 0.0
    top_tvd: float = 0.0
    bottom_tvd: float = 0.0
    pressure_avg_psi: float = 0.0
    temp_avg_f: float = 0.0
    gas_void_fraction: float = 0.0
    gas_volume_bbl: float = 0.0
    mw_effective_ppg: float = 0.0
    dp_hydrostatic_reduction_psi: float = 0.0


@dataclass
class GasResult:
    gas_influx_bbl: float = 0.0
    gas_sg: float = GAS_SG_DEFAULT
    dissolved_fraction: float = 0.0
    free_fraction: float = 0.0
    total_gas_bbl_at_surface: float = 0.0
    total_bhp_reduction_psi: float = 0.0
    total_ecd_reduction_ppg: float = 0.0
    sections: List[GasSectionResult] = field(default_factory=list)


def gas_z_factor(p_psi: float, t_f: float, sg: float = None) -> float:
    """Simple Standing-Katz-like approximation."""
    if sg is None:
        sg = get_param("gas_sg_default", default=GAS_SG_DEFAULT)
    p_pc = 677.0 + 15.0 * (0.6 - sg) * 100.0
    t_pc = 343.0 + 20.0 * (0.6 - sg) * 100.0
    p_pr = max(0.2, p_psi / p_pc)
    t_pr = max(1.05, (t_f + 460.0) / t_pc)
    a = 1.39 * (t_pr - 0.92) ** 0.5 - 0.36 * t_pr - 0.101
    b = ((0.62 - 0.23 * t_pr) * p_pr
         + (0.066 / (t_pr - 0.86) - 0.037) * p_pr ** 2
         + 0.32 * p_pr ** 6 / 10.0 ** (9 * (t_pr - 1.0)))
    c = 0.132 - 0.32 * math.log10(t_pr)
    d = 10.0 ** (0.3106 - 0.49 * t_pr + 0.1824 * t_pr ** 2)
    z = a + (1.0 - a) * math.exp(-b) + c * p_pr ** d
    return max(0.3, min(1.5, z))


def dissolved_gas_fraction(p_psi: float, t_f: float, mw_ppg: float,
                             base: float = None) -> float:
    """Fraction of gas that dissolves in OBM."""
    if base is None:
        base = get_param("gas_solubility_obm",
                          default=GAS_SOLUBILITY_OBM_DEFAULT)
    p_factor = min(1.0, p_psi / 8000.0)
    t_factor = max(0.3, 1.0 - (t_f - 100.0) / 400.0)
    frac = base * p_factor * t_factor
    return max(0.0, min(0.95, frac))


def free_gas_void_fraction(v_gas: float, v_ann: float) -> float:
    return min(0.9, v_gas / v_ann) if v_ann > 0 else 0.0


def mw_with_gas_void(mw_liq: float, void: float) -> float:
    return mw_liq * (1.0 - void)


def compute_gas_behaviour(gas_influx_bbl: float, influx_md: float,
                            string_col, annulus_col, survey,
                            gas_sg: float = GAS_SG_DEFAULT,
                            step_ft: float = 100.0,
                            temp_gradient_f_per_ft: float = 0.015,
                            t_surface_f: float = 90.0,
                            obm_dissolved_base: float = GAS_SOLUBILITY_OBM_DEFAULT
                            ) -> GasResult:
    from arhpp.geometry.survey import md_to_tvd

    res = GasResult(gas_influx_bbl=gas_influx_bbl, gas_sg=gas_sg)
    if gas_influx_bbl <= 0 or not annulus_col.segments:
        return res

    mw_bot = (annulus_col.segments[-1].mw
              if annulus_col.segments else 10.0)
    tvd_influx = md_to_tvd(survey, influx_md) if survey else influx_md
    p_influx = 0.052 * mw_bot * tvd_influx
    t_influx = t_surface_f + temp_gradient_f_per_ft * tvd_influx

    diss = dissolved_gas_fraction(p_influx, t_influx, mw_bot,
                                    obm_dissolved_base)
    res.dissolved_fraction = diss
    res.free_fraction = 1.0 - diss
    free_gas = gas_influx_bbl * res.free_fraction

    total_red = 0.0
    for seg in annulus_col.segments:
        top = seg.top_md
        bot = min(seg.bottom_md, influx_md)
        if bot - top <= 0:
            continue
        md = top
        while md < bot:
            nxt = min(md + step_ft, bot)
            mid = 0.5 * (md + nxt)
            tvd_mid = md_to_tvd(survey, mid) if survey else mid
            t_mid = t_surface_f + temp_gradient_f_per_ft * tvd_mid
            z = gas_z_factor(p_influx, t_mid, gas_sg)
            ref_p = max(p_influx, 100.0)
            ref_t = max(t_influx + 460.0, 100.0)
            ref_z = max(gas_z_factor(ref_p, t_influx, gas_sg), 0.3)
            v_local = (free_gas * (ref_p / max(p_influx, 100.0))
                        * ((t_mid + 460.0) / ref_t) * (z / ref_z))
            frac = (nxt - md) / max(seg.bottom_md - seg.top_md, 1.0)
            seg_vol = seg.volume_bbl * frac
            void = free_gas_void_fraction(v_local, seg_vol)
            mw_eff = mw_with_gas_void(seg.mw, void)
            tvd_a = md_to_tvd(survey, md) if survey else md
            tvd_b = md_to_tvd(survey, nxt) if survey else nxt
            dp_h = (PSI_PER_FT_PER_PPG * (seg.mw - mw_eff)
                    * (tvd_b - tvd_a))
            res.sections.append(GasSectionResult(
                md, nxt, tvd_a, tvd_b, p_influx, t_mid,
                void, v_local, mw_eff, -dp_h))
            total_red += dp_h
            md = nxt

    res.total_gas_bbl_at_surface = free_gas * (
        (p_influx + 14.7) / (1000.0 + 14.7))
    res.total_bhp_reduction_psi = -total_red
    tvd_ref = (annulus_col.segments[-1].bottom_tvd
               if annulus_col.segments else 0.0)
    if tvd_ref > 0:
        res.total_ecd_reduction_ppg = (
            -total_red / (PSI_PER_FT_PER_PPG * tvd_ref))
    return res
