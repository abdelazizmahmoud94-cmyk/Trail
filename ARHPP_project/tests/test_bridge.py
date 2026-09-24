"""Bridge tests."""

import time

from arhpp.sensors.bridge import WITS2PLC, BridgeConfig


def test_bridge_lifecycle():
    bridge = WITS2PLC(BridgeConfig(
        wits_enabled=False, plc_enabled=True,
        plc_rate_hz=20.0, physics_rate_hz=5.0,
        sensor_update_rate_hz=5.0))
    bridge.start()
    time.sleep(0.3)
    stats = bridge.stats()
    assert stats["plc"] is not None
    assert stats["plc"]["cycle_count"] > 0
    bridge.stop()


def test_bridge_arhpp_cache():
    bridge = WITS2PLC(BridgeConfig(
        wits_enabled=False, plc_enabled=False,
        physics_rate_hz=10.0))
    from arhpp.sensors.wits_server import WITSReading
    from datetime import datetime

    fake = WITSReading(
        timestamp=datetime.utcnow(),
        raw={},
        arhpp_inputs={
            "q_in_gpm": 650.0, "q_out_gpm": 780.0,
            "mw_in_ppg": 12.5, "sbp_psi": 250.0,
            "tvd_ft": 15000.0, "spp_psi": 3200.0})
    with bridge._lock:
        bridge._latest_wits = fake
    bridge.start()
    time.sleep(0.5)
    arhpp = bridge.get_arhpp_result()
    assert "bhp_psi" in arhpp
    assert arhpp["bhp_psi"] > 0
    bridge.stop()


def test_bridge_physics_not_blocking():
    bridge = WITS2PLC(BridgeConfig(
        wits_enabled=False, plc_enabled=False))
    bridge.start()
    time.sleep(0.2)
    t0 = time.time()
    for _ in range(1000):
        bridge._get_physics_snapshot()
    elapsed = time.time() - t0
    assert elapsed < 0.5
    bridge.stop()
