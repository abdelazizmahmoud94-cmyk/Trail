"""Visualization tests."""

from arhpp.viz.channel_manager import (
    get_channel_manager, DEFAULT_CHANNELS,
)
from arhpp.viz.graphs import GraphBuilder, GraphSpec
from arhpp.viz.trajectory import TrajectoryEngine
from arhpp.viz.wellbore import WellboreSchematic
from arhpp.viz.trip_tank import VirtualTripTank
from arhpp.core.types import SurveyPoint, HoleSection
from arhpp.geometry.survey import compute_survey


def test_channel_manager_defaults():
    cm = get_channel_manager()
    assert len(cm.list_all()) >= len(DEFAULT_CHANNELS)
    assert cm.get("spp_psi") is not None


def test_channel_metric_conversion():
    cm = get_channel_manager()
    spp = cm.get("spp_psi")
    assert abs(spp.convert_to_metric(1000) - 6895.0) < 1.0


def test_graph_builder_push_and_build():
    gb = GraphBuilder(max_points_per_channel=100)
    for i in range(50):
        gb.push("spp_psi", 3200 + i, time_s=i * 0.1)
    spec = GraphSpec(graph_id="test", channels=["spp_psi"],
                       duration_s=10.0)
    result = gb.build(spec)
    assert "traces" in result


def test_trajectory_3d():
    survey = compute_survey([
        SurveyPoint(0, 0, 0),
        SurveyPoint(1000, 10, 90),
        SurveyPoint(2000, 20, 90)])
    engine = TrajectoryEngine()
    traj = engine.compute_3d(survey)
    assert len(traj.md) == 3
    assert traj.md[-1] == 2000


def test_wellbore_schematic_basic():
    s = WellboreSchematic()
    s.add_casing("Surface", 0, 3000, 18.625, 17.76)
    s.add_open_hole("OH", 3000, 10000, 12.25)
    assert len(s.sections) == 2


def test_wellbore_kuwait_formations():
    s = WellboreSchematic()
    s.kuwait_formations_preload()
    assert len(s.formations) == 26


def test_trip_tank_static():
    tt = VirtualTripTank()
    state = tt.update(bit_md_ft=10000, trip_speed_fps=0.0)
    assert state.direction == "static"


def test_trip_tank_trip_out_increases_volume():
    tt = VirtualTripTank(pipe_displacement_bblft=0.05)
    tt.initial_volume_bbl = 50.0
    tt.current_volume_bbl = 50.0
    tt.update(bit_md_ft=10000, trip_speed_fps=-3.0)
    state = tt.update(bit_md_ft=9700, trip_speed_fps=-3.0)
    assert state.current_volume_bbl > 50.0
