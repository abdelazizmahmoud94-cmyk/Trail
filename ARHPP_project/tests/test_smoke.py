"""Smoke tests — imports + basic functionality."""

from arhpp.core.types import (
    SurveyPoint, FluidSegment, HoleSection, BHASection,
)
from arhpp.geometry.survey import compute_survey, compute_tvd
from arhpp.fluids.rheology import from_fann_6
from arhpp.hydraulics.hydrostatic import hydrostatic_segment
from arhpp.hydraulics.pipe import pipe_section_friction
from arhpp.hydraulics.bit import Nozzle, bit_pressure_drop
from arhpp.flow.effective_flow import reconcile_flow
from arhpp.pore_pressure.dexponent import compute_d_exponent
from arhpp.pore_pressure.kuwait_calibration import pp_ppg_at_md


def test_vertical_well_tvd():
    s = compute_survey([SurveyPoint(0, 0, 0), SurveyPoint(1000, 0, 0)])
    assert abs(s[1].tvd - 1000) < 1e-6


def test_bingham_from_fann():
    r = from_fann_6(74, 46, 38, 28, 8, 6)
    assert r["bingham"].pv == 74 - 46


def test_hydrostatic():
    assert abs(hydrostatic_segment(10.0, 0, 1000) - 520.0) < 1e-6


def test_pipe_friction_positive():
    r = pipe_section_friction(400, 4.276, 100, 10, 15, 0.8, 0.7)
    assert r.dp_psi > 0


def test_bit_dp_q_squared():
    nz = [Nozzle(14), Nozzle(14), Nozzle(14)]
    a = bit_pressure_drop(400, nz, 10)
    b = bit_pressure_drop(800, nz, 10)
    assert abs(b.dp_psi / a.dp_psi - 4.0) < 0.05


def test_flow_balance():
    r = reconcile_flow(600, 0, 0, 600)
    assert r.is_balanced


def test_d_exponent():
    d = compute_d_exponent(60, 120, 25, 8.5)
    assert d > 0


def test_kuwait_pp():
    assert pp_ppg_at_md(12000, 11000) > 9.0
