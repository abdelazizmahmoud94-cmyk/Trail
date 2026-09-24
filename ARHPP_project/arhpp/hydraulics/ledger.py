"""Pressure Ledger composer — BHP / ECD / SPP from decomposed terms."""

from arhpp.core.types import PressureLedger
from arhpp.core.constants import PSI_PER_FT_PER_PPG
from arhpp.hydraulics.hydrostatic import full_hydrostatic
from arhpp.hydraulics.pipe import pipe_friction_total
from arhpp.hydraulics.annular import annular_friction_total
from arhpp.hydraulics.bit import bit_pressure_drop
from arhpp.hydraulics.utube import compute_utube
from arhpp.flow.losses import compute_losses
from arhpp.flow.effective_flow import reconcile_flow


def build_ledger(
    q_pump_gpm: float,
    sbp_psi: float,
    string_col,
    annulus_col,
    bha_sections,
    hole_sections,
    survey,
    nozzles,
    bit_diameter_in: float = 8.5,
    cd: float = 0.95,
    eccentricity: float = 0.5,
    rpm: float = 0.0,
    q_out_measured_gpm: float = None,
    utube_enabled: bool = True,
    choke_closed: bool = False,
) -> dict:
    """
    Full Pressure Ledger.

    BHP = Ph_annulus + Annular_FP + SBP + Loss_effect + Surge + Gas + Kick
    SPP = Bit_dP + Pipe_FP + Annular_FP + SBP - U-Tube + Swab
    """
    L = PressureLedger()

    # --- Hydrostatic (segment-wise) ---
    hyd = full_hydrostatic(string_col, annulus_col, survey)
    L.hydrostatic_string = hyd["string"]["total_psi"]
    L.hydrostatic_annulus = hyd["annulus"]["total_psi"]

    # --- U-Tube as flow driver ---
    utube_res = compute_utube(
        string_col, annulus_col, bha_sections, hole_sections,
        utube_enabled=utube_enabled, choke_closed=choke_closed,
    )
    L.utube = utube_res.dp_utube_psi

    # --- Losses detection ---
    mw_ann = annulus_col.segments[-1].mw if annulus_col.segments else 10.0
    tvd_ref = (annulus_col.segments[-1].bottom_tvd
               if annulus_col.segments
               else (survey[-1].tvd if survey else 0.0))

    ann_baseline = annular_friction_total(
        q_pump_gpm, hole_sections, bha_sections, annulus_col,
        eccentricity=eccentricity, rpm=rpm,
    )

    loss_res = compute_losses(
        q_pump_gpm=q_pump_gpm,
        q_out_gpm=(q_out_measured_gpm if q_out_measured_gpm is not None
                    else q_pump_gpm),
        mw_ppg=mw_ann,
        tvd_ft=tvd_ref,
        annular_fp_psi=ann_baseline["dp_total_psi"],
    )
    L.loss_effect = -loss_res.bhp_reduction_psi

    # --- Effective Flow ---
    flow_res = reconcile_flow(
        q_pump_gpm=q_pump_gpm,
        q_utube_gpm=utube_res.q_utube_gpm,
        q_loss_gpm=loss_res.q_loss_gpm,
        q_out_measured_gpm=q_out_measured_gpm,
    )

    # --- Hydraulics with q_effective ---
    q_eff = max(flow_res.q_effective_annulus, 1.0)

    pipe_res = pipe_friction_total(q_eff, bha_sections, string_col)
    L.pipe_friction = pipe_res["dp_total_psi"]

    ann_res = annular_friction_total(
        q_eff, hole_sections, bha_sections, annulus_col,
        eccentricity=eccentricity, rpm=rpm,
    )
    L.annular_friction = ann_res["dp_total_psi"]

    bit_res = bit_pressure_drop(
        q_gpm=q_eff, nozzles=nozzles, mw_ppg=mw_ann,
        bit_diameter_in=bit_diameter_in, cd=cd,
    )
    L.bit_dp = bit_res.dp_psi

    L.sbp = sbp_psi
    L.tvd_ref = tvd_ref

    # --- BHP ---
    L.bhp = (
        L.hydrostatic_annulus
        + L.annular_friction
        + L.sbp
        + L.loss_effect
        + L.surge + L.gas_effect + L.kick_effect
    )

    # --- ECD ---
    if L.tvd_ref > 0:
        L.ecd = L.bhp / (PSI_PER_FT_PER_PPG * L.tvd_ref)

    # --- SPP closure ---
    spp = (
        L.bit_dp
        + L.pipe_friction
        + L.annular_friction
        + L.sbp
        - L.utube
        + L.swab
    )

    return {
        "ledger": L,
        "spp_psi": spp,
        "pipe": pipe_res,
        "annular": ann_res,
        "annular_baseline": ann_baseline,
        "bit": bit_res,
        "hydrostatic": hyd,
        "utube": utube_res,
        "losses": loss_res,
        "flow": flow_res,
        "q_effective_gpm": q_eff,
    }
