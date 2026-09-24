"""Dynamic BHP Engine — Full integration with cuttings + gas."""

from arhpp.core.types import PressureLedger
from arhpp.core.constants import PSI_PER_FT_PER_PPG
from arhpp.hydraulics.hydrostatic import full_hydrostatic
from arhpp.hydraulics.pipe import pipe_friction_total
from arhpp.hydraulics.annular import annular_friction_total
from arhpp.hydraulics.bit import bit_pressure_drop
from arhpp.hydraulics.surge_swab import compute_surge_swab
from arhpp.hydraulics.utube import compute_utube
from arhpp.cuttings.transport import compute_cuttings_transport
from arhpp.gas.behaviour import compute_gas_behaviour
from arhpp.geometry.survey import md_to_tvd


def dynamic_bhp_full(
    trip_state,
    string_col,
    annulus_col,
    bha_sections,
    hole_sections,
    survey,
    q_pump_gpm: float = 0.0,
    sbp_psi: float = 0.0,
    nozzles=None,
    bit_diameter_in: float = 8.5,
    cd: float = 0.95,
    eccentricity: float = 0.5,
    rpm: float = 0.0,
    rop_ft_hr: float = 0.0,
    gas_influx_bbl: float = 0.0,
    gas_influx_md: float = 0.0,
    gas_sg: float = 0.65,
    obm_dissolved_base: float = 0.35,
) -> dict:
    """Full dynamic BHP combining all engines up to P5."""
    L = PressureLedger()

    # Hydrostatic
    hyd = full_hydrostatic(string_col, annulus_col, survey)
    L.hydrostatic_string = hyd["string"]["total_psi"]
    L.hydrostatic_annulus = hyd["annulus"]["total_psi"]

    # U-Tube
    utube_res = compute_utube(
        string_col, annulus_col, bha_sections, hole_sections)
    L.utube = utube_res.dp_utube_psi

    # Circulation friction
    pipe_res = ann_res = bit_res = None
    if q_pump_gpm > 0:
        pipe_res = pipe_friction_total(q_pump_gpm, bha_sections, string_col)
        L.pipe_friction = pipe_res["dp_total_psi"]
        ann_res = annular_friction_total(
            q_pump_gpm, hole_sections, bha_sections, annulus_col,
            eccentricity=eccentricity, rpm=rpm)
        L.annular_friction = ann_res["dp_total_psi"]
        if nozzles is not None:
            mw_ann = (annulus_col.segments[-1].mw
                       if annulus_col.segments else 10.0)
            bit_res = bit_pressure_drop(
                q_gpm=q_pump_gpm, nozzles=nozzles, mw_ppg=mw_ann,
                bit_diameter_in=bit_diameter_in, cd=cd)
            L.bit_dp = bit_res.dp_psi

    # Surge / Swab
    surge_res = compute_surge_swab(
        bit_md=trip_state.bit_md,
        vp_fps=trip_state.trip_speed_fps,
        closed_end=trip_state.closed_end,
        bha_sections=bha_sections,
        hole_sections=hole_sections,
        annulus_col=annulus_col,
        survey=survey,
    )
    if surge_res.total_dp_psi >= 0:
        L.surge = surge_res.total_dp_psi
    else:
        L.swab = -surge_res.total_dp_psi

    L.sbp = sbp_psi

    # Cuttings
    cut_res = None
    if rop_ft_hr > 0 and q_pump_gpm > 0:
        cut_res = compute_cuttings_transport(
            rop_ft_hr=rop_ft_hr, rpm=rpm, q_gpm=q_pump_gpm,
            hole_sections=hole_sections, bha_sections=bha_sections,
            annulus_col=annulus_col, survey=survey)
        L.annular_friction += cut_res.total_extra_dp_psi

    # Gas
    gas_res = None
    if gas_influx_bbl > 0:
        gas_res = compute_gas_behaviour(
            gas_influx_bbl=gas_influx_bbl,
            influx_md=gas_influx_md,
            string_col=string_col, annulus_col=annulus_col,
            survey=survey, gas_sg=gas_sg,
            obm_dissolved_base=obm_dissolved_base)
        L.gas_effect = gas_res.total_bhp_reduction_psi

    # TVD ref
    L.tvd_ref = (md_to_tvd(survey, trip_state.bit_md)
                 if survey else trip_state.bit_md)

    # BHP
    L.bhp = (
        L.hydrostatic_annulus
        + L.annular_friction
        + L.sbp
        + L.surge - L.swab
        + L.gas_effect
        + L.loss_effect
        + L.kick_effect
    )

    if L.tvd_ref > 0:
        L.ecd = L.bhp / (PSI_PER_FT_PER_PPG * L.tvd_ref)

    esd_p = (L.hydrostatic_annulus + L.surge - L.swab + L.gas_effect)
    esd = (esd_p / (PSI_PER_FT_PER_PPG * L.tvd_ref)
           if L.tvd_ref > 0 else 0.0)

    return {
        "ledger": L,
        "surge_result": surge_res,
        "cuttings": cut_res,
        "gas": gas_res,
        "hydrostatic": hyd,
        "utube": utube_res,
        "pipe": pipe_res,
        "annular": ann_res,
        "bit": bit_res,
        "bhp_psi": L.bhp,
        "ecd_ppg": L.ecd,
        "esd_ppg": esd,
        "tvd_bit_ft": L.tvd_ref,
    }
