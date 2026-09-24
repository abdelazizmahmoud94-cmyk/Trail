"""Objective function — reads params from context (not global)."""

from typing import Dict, List, Optional

from arhpp.calibration.context import get_param
from arhpp.calibration.targets import compute_well_target, WellTarget


def run_well_evaluation(well,
                          weights: Optional[Dict] = None) -> WellTarget:
    """
    Run ARHPP on one well. Reads parameters from current context.
    Does NOT mutate any module.
    """
    from arhpp.core.types import (
        FluidSegment, HoleSection, BHASection, SurveyPoint,
    )
    from arhpp.geometry.survey import compute_survey
    from arhpp.fluids.rheology import from_fann_6
    from arhpp.fluids.fluid_tracking import FluidColumn
    from arhpp.hydraulics.ledger import build_ledger
    from arhpp.hydraulics.bit import Nozzle
    from arhpp.events.kick import KickInputs, compute_kick
    from arhpp.pore_pressure.kuwait_calibration import pp_ppg_at_md

    survey = compute_survey([
        SurveyPoint(md=0.0, inc=0.0, azi=0.0),
        SurveyPoint(md=well.md_ft, inc=0.0, azi=0.0),
    ])

    section = HoleSection(
        name="OH", hole_id_in=well.hole_id_in,
        top_md=0.0, bottom_md=well.md_ft)
    sections = [section]
    bha = [BHASection(
        name="DP", component_type="DP",
        od_in=well.pipe_od_in, id_in=well.pipe_id_in,
        length_ft=well.md_ft)]

    hb = from_fann_6(
        well.fann_600, well.fann_300, well.fann_200,
        well.fann_100, well.fann_6, well.fann_3)["herschel_bulkley"]

    k_temp = get_param("k_temp_factor")
    tau_temp = get_param("tau_y_temp_factor")
    k_corr = hb.k * k_temp
    tau_corr = hb.tau_y * tau_temp

    def _mk_seg(mw):
        s = FluidSegment(
            fluid_id="MUD", mw=mw,
            top_md=0.0, bottom_md=well.md_ft,
            top_tvd=0.0, bottom_tvd=well.tvd_ft)
        s.tau_y = tau_corr
        s.k = k_corr
        s.n = hb.n
        return s

    mw_string = well.mw_in_ppg
    if abs(well.mw_in_ppg - well.mw_out_ppg) > 1.0:
        mw_annulus = 0.5 * (well.mw_in_ppg + well.mw_out_ppg)
    else:
        mw_annulus = well.mw_out_ppg

    string_col = FluidColumn([_mk_seg(mw_string)])
    ann_col = FluidColumn([_mk_seg(mw_annulus)])

    nozzles = [Nozzle(size_32nd_in=14, tfa_in2=well.tfa_in2)]

    bundle = build_ledger(
        q_pump_gpm=well.q_gpm,
        sbp_psi=well.sbp_psi,
        string_col=string_col,
        annulus_col=ann_col,
        bha_sections=bha,
        hole_sections=sections,
        survey=survey,
        nozzles=nozzles,
        bit_diameter_in=well.hole_id_in,
        cd=well.cd,
        eccentricity=well.eccentricity,
        rpm=well.rpm,
        q_out_measured_gpm=well.q_out_measured_gpm)
    L = bundle["ledger"]

    kick = compute_kick(KickInputs(
        q_in_gpm=well.q_gpm,
        q_out_gpm=well.q_out_measured_gpm or well.q_gpm,
        tvd_ft=well.tvd_ft,
        mw_ppg=well.mw_in_ppg,
        annular_fp_psi=L.annular_friction,
        sbp_psi=well.sbp_psi))

    pp_ref = pp_ppg_at_md(well.md_ft, well.tvd_ft)

    return compute_well_target(
        well=well,
        pred_bhp=L.bhp,
        pred_ecd=L.ecd,
        pred_spp=bundle["spp_psi"],
        pred_pp=pp_ref,
        pred_kick_severity=kick.severity,
        pred_loss_class=bundle["losses"].loss_class,
        weights=weights)


def objective(params: Dict[str, float],
                wells: List) -> float:
    """Global objective = mean of per-well composite errors."""
    from arhpp.calibration.profile import CalibrationProfile
    from arhpp.calibration.context import param_context

    if not wells:
        return 0.0

    temp_profile = CalibrationProfile(
        name="__temp_optimizer__", values=params)

    total = 0.0
    with param_context(temp_profile, context_name="OPTIMIZER"):
        for w in wells:
            try:
                t = run_well_evaluation(w)
                total += t.composite
            except Exception:
                total += 1.0
    return total / len(wells)


def evaluate_all(params: Dict[str, float],
                   wells: List) -> List[WellTarget]:
    from arhpp.calibration.profile import CalibrationProfile
    from arhpp.calibration.context import param_context

    temp_profile = CalibrationProfile(name="__temp_eval__", values=params)
    with param_context(temp_profile, context_name="EVAL"):
        return [run_well_evaluation(w) for w in wells]
