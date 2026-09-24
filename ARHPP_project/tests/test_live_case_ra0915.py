"""Live Case RA-0915 (23-Sep-2026) validation test.

Reference:
    Q_in = 199.3 gpm, Q_out = 201 gpm
    MW_in = 13.50 ppg, MW_out = 10.69 ppg
    SPP = 47.5 psi, SBP = 27.5 psi
    TVD = 15690 ft
    PWD BHP = 9266 psi, PWD ECD = 11.37 ppg
"""

from arhpp.core.constants import (
    LIVE_CASE_RA0915, PSI_PER_FT_PER_PPG,
)
from arhpp.core.types import (
    FluidSegment, HoleSection, BHASection, SurveyPoint,
)
from arhpp.geometry.survey import compute_survey
from arhpp.fluids.fluid_tracking import FluidColumn
from arhpp.hydraulics.hydrostatic import full_hydrostatic
from arhpp.hydraulics.ledger import build_ledger
from arhpp.hydraulics.bit import Nozzle


def _make_well_15k():
    survey = compute_survey([
        SurveyPoint(0, 0, 0),
        SurveyPoint(15690, 0, 0),
    ])
    sections = [
        HoleSection("CSG", 17.239, 0, 5759,
                     casing_id_in=15.0, casing_shoe_md=5759),
        HoleSection("OH", 16.0, 5759, 15690),
    ]
    bha = [BHASection("DP", "DP", 5.5, 4.56, 15690)]
    return survey, sections, bha


def _make_col(mw):
    seg = FluidSegment("MUD", mw, 0, 15690,
                        top_tvd=0, bottom_tvd=15690)
    seg.tau_y, seg.k, seg.n = 3.895, 0.0822, 0.92
    return FluidColumn([seg])


def test_pwd_ecd_matches_bhp():
    bhp = LIVE_CASE_RA0915["pwd_bhp_psi"]
    tvd = LIVE_CASE_RA0915["tvd_ft"]
    ecd = bhp / (PSI_PER_FT_PER_PPG * tvd)
    assert abs(ecd - LIVE_CASE_RA0915["pwd_ecd_ppg"]) < 0.1


def test_hydrostatic_with_mw_in_overestimates():
    survey, _, _ = _make_well_15k()
    sc = _make_col(LIVE_CASE_RA0915["mw_in_ppg"])
    ac = _make_col(LIVE_CASE_RA0915["mw_in_ppg"])
    hyd = full_hydrostatic(sc, ac, survey)
    assert hyd["annulus"]["total_psi"] > (
        LIVE_CASE_RA0915["pwd_bhp_psi"] + 1000)


def test_hydrostatic_with_mw_out_underestimates():
    survey, _, _ = _make_well_15k()
    sc = _make_col(LIVE_CASE_RA0915["mw_out_ppg"])
    ac = _make_col(LIVE_CASE_RA0915["mw_out_ppg"])
    hyd = full_hydrostatic(sc, ac, survey)
    assert hyd["annulus"]["total_psi"] < LIVE_CASE_RA0915["pwd_bhp_psi"]


def test_effective_annular_mw_matches_pwd():
    survey, _, _ = _make_well_15k()
    mw_eff = LIVE_CASE_RA0915["mw_annulus_eff_ppg"]
    sc = _make_col(LIVE_CASE_RA0915["mw_in_ppg"])
    ac = _make_col(mw_eff)
    hyd = full_hydrostatic(sc, ac, survey)
    hydro_eff = hyd["annulus"]["total_psi"]
    estimated_bhp = hydro_eff + LIVE_CASE_RA0915["sbp_psi"]
    target = LIVE_CASE_RA0915["pwd_bhp_psi"]
    assert abs(estimated_bhp - target) < 100


def test_kuwait_formations_loaded():
    from arhpp.pore_pressure.kuwait_calibration import kuwait_table
    tbl = kuwait_table()
    names = [r["Name"] for r in tbl]
    assert "Zubair_top" in names
    assert "Mid_Marrat_top" in names
    mid_marrat = next(r for r in tbl if r["Name"] == "Mid_Marrat_top")
    assert abs(mid_marrat["PP_ref_ppg"] - 12.5) < 0.01
