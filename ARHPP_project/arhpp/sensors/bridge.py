"""WITS -> ARHPP -> PLC Sim Bridge."""

import threading
import logging
import time
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any

from arhpp.sensors.wits_server import WITSReceiver, WITSReading
from arhpp.plc.simulator import (
    PLCSimulator, SimulatorConfig, PhysicsSnapshot,
)

log = logging.getLogger(__name__)


@dataclass
class BridgeConfig:
    physics_rate_hz: float = 10.0
    sensor_update_rate_hz: float = 10.0
    wits_enabled: bool = True
    wits_port: int = 14200
    plc_enabled: bool = True
    plc_rate_hz: float = 50.0
    wits_out_enabled: bool = False
    wits_out_host: str = "127.0.0.1"
    wits_out_port: int = 14201


class WITS2PLC:
    def __init__(self, config: Optional[BridgeConfig] = None,
                 arhpp_compute_fn: Optional[Callable] = None):
        self.config = config or BridgeConfig()
        self.arhpp_compute_fn = arhpp_compute_fn or compute_arhpp_default
        self.wits_receiver: Optional[WITSReceiver] = None
        self.plc: Optional[PLCSimulator] = None
        self._lock = threading.RLock()
        self._latest_wits: Optional[WITSReading] = None
        self._latest_arhpp: Dict[str, Any] = {}
        self._latest_physics_snapshot: PhysicsSnapshot = PhysicsSnapshot()
        self._stop_event = threading.Event()
        self._physics_thread: Optional[threading.Thread] = None
        self._sensor_thread: Optional[threading.Thread] = None
        self._physics_cycles: int = 0
        self._sensor_cycles: int = 0
        self._wits_readings: int = 0
        self._start_time: float = 0.0

    def start(self) -> None:
        self._start_time = time.time()
        if self.config.wits_enabled:
            self.wits_receiver = WITSReceiver(
                host="0.0.0.0", port=self.config.wits_port,
                on_reading=self._on_wits_reading)
            self.wits_receiver.start()
        if self.config.plc_enabled:
            self.plc = PLCSimulator(
                config=SimulatorConfig(
                    rt_loop_hz=self.config.plc_rate_hz,
                    enable_wits_out=self.config.wits_out_enabled,
                    wits_out_host=self.config.wits_out_host,
                    wits_out_port=self.config.wits_out_port),
                physics_provider=self._get_physics_snapshot)
            self.plc.start()
        self._physics_thread = threading.Thread(
            target=self._physics_loop, name="ARHPPPhysics", daemon=True)
        self._physics_thread.start()
        self._sensor_thread = threading.Thread(
            target=self._sensor_loop, name="SensorBridge", daemon=True)
        self._sensor_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self.wits_receiver:
            self.wits_receiver.stop()
        if self.plc:
            self.plc.stop()
        if self._physics_thread:
            self._physics_thread.join(timeout=3.0)
        if self._sensor_thread:
            self._sensor_thread.join(timeout=3.0)

    def _on_wits_reading(self, reading: WITSReading) -> None:
        with self._lock:
            self._latest_wits = reading
            self._wits_readings += 1

    def _physics_loop(self) -> None:
        interval = 1.0 / self.config.physics_rate_hz
        next_cycle = time.time()
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    wits = self._latest_wits
                if wits is not None:
                    try:
                        arhpp_result = self.arhpp_compute_fn(
                            wits.arhpp_inputs)
                    except Exception as e:
                        log.exception(f"ARHPP compute failed: {e}")
                        arhpp_result = {}
                    with self._lock:
                        self._latest_arhpp = arhpp_result
                        self._latest_physics_snapshot = PhysicsSnapshot(
                            q_in_gpm=wits.arhpp_inputs.get("q_in_gpm", 0.0),
                            q_out_gpm=wits.arhpp_inputs.get("q_out_gpm", 0.0),
                            pit_gain_bbl=wits.arhpp_inputs.get(
                                "pit_gain_bbl", 0.0),
                            bhp_predicted_psi=arhpp_result.get(
                                "bhp_psi", 9500.0),
                            bg_gas_units=wits.arhpp_inputs.get("gas_bg", 0.0),
                            cg_gas_units=wits.arhpp_inputs.get("gas_cg", 0.0),
                            tg_gas_units=wits.arhpp_inputs.get("gas_tg", 0.0),
                            tvd_ft=wits.arhpp_inputs.get("tvd_ft", 15000.0),
                            mw_ppg=wits.arhpp_inputs.get("mw_in_ppg", 12.0),
                            annular_fp_psi=arhpp_result.get(
                                "annular_fp_psi", 300.0),
                            timestamp=time.time())
                        self._physics_cycles += 1
            except Exception as e:
                log.exception(f"Physics loop error: {e}")
            next_cycle += interval
            sleep_time = next_cycle - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_cycle = time.time()

    def _sensor_loop(self) -> None:
        interval = 1.0 / self.config.sensor_update_rate_hz
        next_cycle = time.time()
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    wits = self._latest_wits
                if wits is not None and self.plc is not None:
                    inputs = wits.arhpp_inputs
                    if "spp_psi" in inputs:
                        self.plc.set_sensor("SPP", inputs["spp_psi"])
                    if "sbp_psi" in inputs:
                        self.plc.set_sensor("SBP", inputs["sbp_psi"])
                    if "wellhead_pressure_psi" in inputs:
                        self.plc.set_sensor(
                            "Wellhead Pressure",
                            inputs["wellhead_pressure_psi"])
                    if "pwd_bhp_psi" in inputs:
                        self.plc.set_sensor("PWD BHP", inputs["pwd_bhp_psi"])
                    with self._lock:
                        self._sensor_cycles += 1
            except Exception as e:
                log.exception(f"Sensor loop error: {e}")
            next_cycle += interval
            sleep_time = next_cycle - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_cycle = time.time()

    def _get_physics_snapshot(self) -> PhysicsSnapshot:
        with self._lock:
            return self._latest_physics_snapshot

    def get_arhpp_result(self) -> Dict:
        with self._lock:
            return dict(self._latest_arhpp)

    def get_latest_wits(self):
        with self._lock:
            return self._latest_wits

    def stats(self) -> Dict:
        with self._lock:
            return {
                "uptime_s": round(time.time() - self._start_time, 1),
                "physics_cycles": self._physics_cycles,
                "sensor_cycles": self._sensor_cycles,
                "wits_readings": self._wits_readings,
                "physics_rate_actual_hz": round(
                    self._physics_cycles / max(
                        time.time() - self._start_time, 1e-3), 2),
                "plc": (self.plc.get_status().to_dict()
                         if self.plc else None),
            }


def compute_arhpp_default(wits_inputs: Dict) -> Dict:
    q_in = wits_inputs.get("q_in_gpm", 0.0)
    q_out = wits_inputs.get("q_out_gpm", 0.0)
    mw = wits_inputs.get("mw_in_ppg", 12.0)
    sbp = wits_inputs.get("sbp_psi", 0.0)
    tvd = wits_inputs.get("tvd_ft", 15000.0)
    hydro = 0.052 * mw * tvd
    ann_fp = 300.0
    bhp = hydro + ann_fp + sbp
    return {
        "bhp_psi": bhp,
        "ecd_ppg": bhp / (0.052 * tvd) if tvd > 0 else 0.0,
        "annular_fp_psi": ann_fp,
        "kick_probability": 0.8 if (q_out - q_in) > 50 else 0.1,
        "loss_fraction": (max(0.0, (q_in - q_out) / q_in)
                            if q_in > 0 else 0.0),
    }
