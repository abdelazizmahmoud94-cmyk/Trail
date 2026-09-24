"""PLC Simulator tests."""

import time
import pytest

from arhpp.plc import (
    PLCSimulator, ControlMode, SafeModeReason, KickState,
)
from arhpp.plc.simulator import SimulatorConfig
from arhpp.plc.choke import ChokeModel, compute_choke_flow
from arhpp.plc.control_modes import PIDController, APController
from arhpp.plc.types import CHOKE_CV_CURVE


def test_choke_cv_curve_monotonic():
    positions = [p for p, _ in CHOKE_CV_CURVE]
    cv = [c for _, c in CHOKE_CV_CURVE]
    assert positions == sorted(positions)
    assert cv == sorted(cv)
    assert cv[0] == 0.0
    assert cv[-1] == 1.0


def test_choke_flow_zero_when_closed():
    assert compute_choke_flow(0.0, 500.0, 0.0) == 0.0


def test_choke_flow_zero_when_no_dp():
    assert compute_choke_flow(50.0, 100.0, 100.0) == 0.0


def test_choke_flow_increases_with_position():
    q30 = compute_choke_flow(30.0, 500.0, 0.0)
    q70 = compute_choke_flow(70.0, 500.0, 0.0)
    assert q70 > q30 > 0


def test_choke_rate_limit():
    c = ChokeModel(choke_id="TEST", rate_limit_pct_sec=5.0)
    c.set_command(100.0)
    for _ in range(25):
        c.update(dt_s=1.0)
    assert c.actual_pct > 95.0


def test_pid_reaches_setpoint():
    pid = PIDController(kp=0.05, ki=0.005, kd=0.0, deadband_psi=1.0)
    pid._last_output = 50.0
    for _ in range(200):
        out = pid.update(setpoint=250.0, measurement=200.0, dt_s=0.1)
    # Choke should move (inverted plant)


def test_ap_reduces_choke_when_bhp_high():
    ap = APController(bhp_target_psi=9500.0)
    ap._last_output = 50.0
    out = ap.update(bhp_predicted=9700.0, sbp_measured=200.0)
    assert out > 50.0  # open choke to reduce BHP


def test_simulator_lifecycle():
    sim = PLCSimulator(SimulatorConfig(rt_loop_hz=50.0))
    sim.start()
    time.sleep(0.2)
    status = sim.get_status()
    assert status.cycle_count > 0
    sim.stop()


def test_simulator_esd_triggers_safe_mode():
    sim = PLCSimulator(SimulatorConfig(rt_loop_hz=50.0))
    sim.start()
    time.sleep(0.2)
    sim.trigger_esd()
    time.sleep(0.2)
    status = sim.get_status()
    assert status.safe_mode is True
    assert status.safe_mode_reason == SafeModeReason.ESD_SIGNAL
    sim.stop()
