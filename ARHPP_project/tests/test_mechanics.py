"""Mechanics tests."""

from arhpp.core.types import SurveyPoint, BHASection
from arhpp.geometry.survey import compute_survey
from arhpp.mechanics.types import (
    TDInputs, OperationType, BucklingType,
)
from arhpp.mechanics.torque_drag import TorqueDragEngine
from arhpp.mechanics.buckling import BucklingEngine
from arhpp.mechanics.overpull import compute_overpull
from arhpp.mechanics.jar import compute_jar_impact, JarType
from arhpp.mechanics.limits import LimitsChecker


def _make_survey():
    return compute_survey([
        SurveyPoint(0, 0, 0),
        SurveyPoint(3000, 5, 90),
        SurveyPoint(6000, 15, 90),
        SurveyPoint(10000, 30, 90),
        SurveyPoint(15000, 35, 95)])


def _make_bha():
    bha = [
        BHASection("DP", "DP", 5.0, 4.276, 12000),
        BHASection("HWDP", "HWDP", 5.0, 3.0, 600),
        BHASection("DC", "DC", 6.5, 2.8125, 360),
        BHASection("Bit", "Bit", 8.5, 1.5, 1)]
    td_md = 15000.0
    cursor = td_md
    for sec in reversed(bha):
        sec.bottom_md = cursor
        sec.top_md = cursor - sec.length_ft
        cursor = sec.top_md
    return bha


def test_buckling_none_for_low_load():
    bk = BucklingEngine()
    th = bk.check_buckling(
        od_in=5.0, id_in=4.276, inc_deg=30, dls=1.0,
        axial_load_klb=5.0, mw_ppg=12.0, hole_id_in=8.5)
    assert th.buckling_type == BucklingType.NONE


def test_overpull_normal():
    r = compute_overpull(free_hookload_klb=200.0,
                          current_hookload_klb=210.0)
    assert r.status == "normal"


def test_overpull_elevated():
    r = compute_overpull(free_hookload_klb=200.0,
                          current_hookload_klb=270.0)
    assert r.status == "elevated"


def test_overpull_critical():
    r = compute_overpull(free_hookload_klb=200.0,
                          current_hookload_klb=540.0,
                          string_yield_klb=550.0)
    assert r.status == "critical"


def test_jar_impact_computes():
    r = compute_jar_impact(overpull_klb=200.0,
                            hammer_length_in=6.0,
                            jar_type=JarType.HYDRAULIC)
    assert r["max_force_at_jar_klb"] > 200.0
    assert r["impact_energy_ftlb"] > 0


def test_limits_normal():
    lc = LimitsChecker()
    report = lc.check_all(hookload_klb=300.0,
                            surface_torque_ftlb=8000.0)
    assert report.overall_status == "ok"


def test_limits_critical():
    lc = LimitsChecker()
    report = lc.check_all(hookload_klb=800.0,
                            surface_torque_ftlb=8000.0)
    assert report.overall_status == "critical"
