"""PLCSimulator — combines all components."""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from threading import Thread, Lock, Event
from typing import Optional, Dict, Callable, List

from arhpp.plc.analog_io import AnalogIOBank
from arhpp.plc.choke import ChokeModel
from arhpp.plc.control_modes import ChokeModeManager
from arhpp.plc.digital_io import DigitalIO
from arhpp.plc.kick_auto import KickAutoController, KickAutoConfig
from arhpp.plc.types import (
    ControlMode, PLCStatus, SafeModeReason, SensorValue, ChokeFeedback,
)
from arhpp.plc.watchdog import Watchdog, SafeModeManager

log = logging.getLogger(__name__)


@dataclass
class PhysicsSnapshot:
    q_in_gpm: float = 0.0
    q_out_gpm: float = 0.0
    pit_gain_bbl: float = 0.0
    bhp_predicted_psi: float = 9500.0
    bg_gas_units: float = 0.0
    cg_gas_units: float = 0.0
    tg_gas_units: float = 0.0
    tvd_ft: float = 15000.0
    mw_ppg: float = 12.0
    annular_fp_psi: float = 300.0
    timestamp: float = 0.0


@dataclass
class SimulatorConfig:
    rt_loop_hz: float = 100.0
    watchdog_timeout_s: float = 0.5
    enable_kick_auto: bool = True
    enable_wits_out: bool = False
    wits_out_host: str = "127.0.0.1"
    wits_out_port: int = 14201
    wits_out_rate_hz: float = 1.0
    physics_cache_ttl_s: float = 0.2
    ssp_initial_psi: float = 250.0
    bhp_initial_psi: float = 9500.0


class PLCSimulator:
    def __init__(self, config: Optional[SimulatorConfig] = None,
                 physics_provider: Optional[Callable] = None):
        self.config = config or SimulatorConfig()
        self.physics_provider = physics_provider
        self.ai = AnalogIOBank()
        self.di = DigitalIO()
        self.choke_a = ChokeModel(choke_id="CHOKE-A")
        self.choke_b = ChokeModel(choke_id="CHOKE-B")
        self.mode_a = ChokeModeManager(self.choke_a)
        self.mode_b = ChokeModeManager(self.choke_b)
        self.watchdog = Watchdog(timeout_s=self.config.watchdog_timeout_s)
        self.safe = SafeModeManager()
        self.kick_auto = KickAutoController(KickAutoConfig())

        # WITS Out (optional)
        self.wits_sender = None
        if self.config.enable_wits_out:
            try:
                from arhpp.sensors.wits_server import WITSSender
                self.wits_sender = WITSSender(
                    self.config.wits_out_host, self.config.wits_out_port)
            except Exception as e:
                log.warning(f"WITS Out init failed: {e}")

        self._thread: Optional[Thread] = None
        self._stop_event = Event()
        self._lock = Lock()
        self._last_sensors: Dict[str, SensorValue] = {}
        self._last_choke_feedback: Dict[str, dict] = {}
        self._last_physics: PhysicsSnapshot = PhysicsSnapshot()
        self._physics_cache: Optional[PhysicsSnapshot] = None
        self._physics_cache_ts: float = 0.0
        self._last_wits_out_ts: float = 0.0

        self._status = PLCStatus(
            start_time=datetime.utcnow(),
            target_cycle_ms=1000.0 / self.config.rt_loop_hz)
        self._callbacks: List[Callable] = []
        self.safe.register_callback(self._on_safe_mode_activated)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._rt_loop, name="PLCSimRT",
                                daemon=True)
        self._thread.start()
        log.info(f"PLC Simulator started at {self.config.rt_loop_hz} Hz")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        if self.wits_sender:
            self.wits_sender.close()
        log.info("PLC Simulator stopped")

    def register_callback(self, cb: Callable) -> None:
        self._callbacks.append(cb)

    def set_choke_mode(self, choke_id: str, mode: ControlMode,
                         setpoint_psi: float = 0.0) -> None:
        with self._lock:
            mgr = self._mode_mgr(choke_id)
            if mgr:
                mgr.set_mode(mode, setpoint_psi)
                if choke_id == "CHOKE-A":
                    self.di.set_input("CHOKE_A_AUTO",
                                       mode != ControlMode.MANUAL)
                elif choke_id == "CHOKE-B":
                    self.di.set_input("CHOKE_B_AUTO",
                                       mode != ControlMode.MANUAL)

    def set_choke_position(self, choke_id: str,
                             position_pct: float) -> None:
        with self._lock:
            mgr = self._mode_mgr(choke_id)
            if mgr and mgr.mode == ControlMode.MANUAL:
                mgr.choke.set_command(position_pct,
                                        mode=ControlMode.MANUAL,
                                        source="operator")

    def set_sensor(self, name: str, value: float) -> None:
        channel_id = self._channel_id_from_name(name)
        if channel_id:
            self.ai.set_input(channel_id, value)

    def get_sensor(self, name: str) -> Optional[SensorValue]:
        channel_id = self._channel_id_from_name(name)
        if channel_id:
            with self._lock:
                return self._last_sensors.get(channel_id)
        return None

    @staticmethod
    def _channel_id_from_name(name: str) -> Optional[str]:
        return {"SPP": "AI-0", "SBP": "AI-1",
                 "Wellhead Pressure": "AI-2",
                 "PWD BHP": "AI-3"}.get(name)

    def get_choke_feedback(self, choke_id: str) -> Optional[dict]:
        with self._lock:
            return self._last_choke_feedback.get(choke_id)

    def get_status(self) -> PLCStatus:
        self._update_status()
        with self._lock:
            return PLCStatus(**self._status.to_dict())

    def trigger_esd(self) -> None:
        self.di.set_input("ESD_ACTIVE", True)
        self.safe.activate(SafeModeReason.ESD_SIGNAL, "ESD triggered")

    def clear_esd(self) -> None:
        self.di.set_input("ESD_ACTIVE", False)

    def trigger_safe_mode(self,
                            reason: SafeModeReason = SafeModeReason.MANUAL_TRIGGER,
                            note: str = "") -> None:
        self.safe.activate(reason, note)

    def clear_safe_mode(self, note: str = "manual clear") -> None:
        self.safe.clear(note)
        self.choke_a.clear_fail_safe()
        self.choke_b.clear_fail_safe()

    def kick_auto_arm(self) -> None:
        self.kick_auto.arm()

    def kick_auto_disarm(self) -> None:
        self.kick_auto.disarm()

    def _mode_mgr(self, choke_id: str) -> Optional[ChokeModeManager]:
        return {"CHOKE-A": self.mode_a, "CHOKE-B": self.mode_b}.get(choke_id)

    def _on_safe_mode_activated(self, reason: SafeModeReason) -> None:
        log.warning(f"SAFE MODE: {reason.value}")
        self.choke_a.trigger_fail_safe(0.0)
        self.choke_b.trigger_fail_safe(0.0)
        self.mode_a.set_mode(ControlMode.SAFE)
        self.mode_b.set_mode(ControlMode.SAFE)
        self.di.set_output("PUMP_1_START", False)
        self.di.set_output("PUMP_2_START", False)
        self.di.set_output("AUX_PUMP_START", False)
        self.di.set_output("ALARM_BEACON", True)
        self.di.set_output("ALARM_HORN", True)

    def _fetch_physics(self) -> PhysicsSnapshot:
        now = time.time()
        if (self._physics_cache is not None
                and now - self._physics_cache_ts
                < self.config.physics_cache_ttl_s):
            return self._physics_cache
        if self.physics_provider is None:
            snap = PhysicsSnapshot(timestamp=now)
        else:
            try:
                snap = self.physics_provider() or PhysicsSnapshot()
                snap.timestamp = now
            except Exception as e:
                log.warning(f"physics_provider failed: {e}")
                snap = PhysicsSnapshot(timestamp=now)
        self._physics_cache = snap
        self._physics_cache_ts = now
        return snap

    def _rt_loop(self) -> None:
        target_dt = 1.0 / self.config.rt_loop_hz
        next_cycle = time.time()
        wits_interval = 1.0 / max(self.config.wits_out_rate_hz, 0.01)

        while not self._stop_event.is_set():
            t_start = time.time()

            if self.watchdog.check_timeout():
                self.safe.activate(SafeModeReason.WATCHDOG_TIMEOUT,
                                     "watchdog timeout")

            physics = self._fetch_physics()
            with self._lock:
                self._last_physics = physics

            new_sensors = self.ai.read_all_inputs(dt_s=target_dt)
            with self._lock:
                self._last_sensors = new_sensors
            sbp_val = new_sensors.get("AI-1")
            sbp_psi = sbp_val.value if sbp_val else 0.0

            esd = self.di.read_input("ESD_ACTIVE")
            if esd and not self.safe.active:
                self.safe.activate(SafeModeReason.ESD_SIGNAL, "DI ESD")

            if (self.config.enable_kick_auto
                    and self.kick_auto.state.value != "DISARMED"):
                kick_action = self.kick_auto.update(
                    dt_s=target_dt,
                    q_in_gpm=physics.q_in_gpm,
                    q_out_gpm=physics.q_out_gpm,
                    pit_gain_bbl=physics.pit_gain_bbl,
                    sbp_measured_psi=sbp_psi,
                    bg_gas=physics.bg_gas_units,
                    cg_gas=physics.cg_gas_units,
                    tg_gas=physics.tg_gas_units,
                    tvd_ft=physics.tvd_ft,
                    mw_ppg=physics.mw_ppg,
                    annular_fp_psi=physics.annular_fp_psi)
                if kick_action.get("action") == "RAMP_SBP":
                    target = kick_action.get("target_sbp_psi", sbp_psi)
                    self.mode_a.set_mode(ControlMode.COMPUTER, target)

            with self._lock:
                up_a = sbp_psi + 500.0
                pos_a = self.mode_a.update(
                    dt_s=target_dt, sbp_measured=sbp_psi,
                    bhp_predicted=physics.bhp_predicted_psi)
                self.ai.set_output("AO-0", pos_a)
                fb_a = self.choke_a.update(
                    dt_s=target_dt, upstream_psi=up_a, downstream_psi=0.0)
                self._last_choke_feedback["CHOKE-A"] = fb_a

                pos_b = self.mode_b.update(
                    dt_s=target_dt, sbp_measured=sbp_psi,
                    bhp_predicted=physics.bhp_predicted_psi)
                self.ai.set_output("AO-1", pos_b)
                fb_b = self.choke_b.update(
                    dt_s=target_dt, upstream_psi=up_a, downstream_psi=0.0)
                self._last_choke_feedback["CHOKE-B"] = fb_b

            self.ai.update_outputs(dt_s=target_dt)

            if self.wits_sender is not None:
                now = time.time()
                if now - self._last_wits_out_ts >= wits_interval:
                    self._last_wits_out_ts = now
                    try:
                        self.wits_sender.send({
                            "bhp_psi": physics.bhp_predicted_psi,
                            "ecd_ppg": 0.0,
                            "sbp_psi": sbp_psi,
                            "wellhead_pressure_psi": (
                                new_sensors.get("AI-2").value
                                if new_sensors.get("AI-2") else 0.0),
                        })
                    except Exception as e:
                        log.warning(f"WITS Out send failed: {e}")

            self.watchdog.kick()

            cycle_ms = (time.time() - t_start) * 1000.0
            with self._lock:
                self._status.cycle_time_ms = cycle_ms
                self._status.cycle_count += 1
                self._status.uptime_sec = (
                    datetime.utcnow() - self._status.start_time
                ).total_seconds()
                self._status.safe_mode = self.safe.active
                self._status.safe_mode_reason = self.safe.reason
                self._status.watchdog_ok = self.watchdog.is_ok()

            snapshot = self._build_snapshot()
            for cb in self._callbacks:
                try:
                    cb(snapshot)
                except Exception as e:
                    log.exception(f"callback failed: {e}")

            next_cycle += target_dt
            sleep_time = next_cycle - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_cycle = time.time()

    def _build_snapshot(self) -> Dict:
        with self._lock:
            return {
                "timestamp": time.time(),
                "status": self._status.to_dict(),
                "sensors": {
                    k: {"value": v.value, "unit": v.unit,
                         "quality": v.quality.value}
                    for k, v in self._last_sensors.items()
                },
                "chokes": {
                    k: {"commanded_pct": f["commanded_pct"],
                         "actual_pct": f["actual_pct"],
                         "state": f["state"],
                         "flow_gpm": f["flow_gpm"]}
                    for k, f in self._last_choke_feedback.items()
                },
                "modes": {"CHOKE-A": self.mode_a.info(),
                            "CHOKE-B": self.mode_b.info()},
                "physics": {
                    "q_in_gpm": self._last_physics.q_in_gpm,
                    "q_out_gpm": self._last_physics.q_out_gpm,
                    "pit_gain_bbl": self._last_physics.pit_gain_bbl,
                    "bhp_predicted_psi": self._last_physics.bhp_predicted_psi,
                },
                "digital_inputs": self.di.read_all_inputs(),
                "digital_outputs": self.di.read_all_outputs(),
                "safe_mode": self.safe.info(),
                "kick_auto": self.kick_auto.info(),
            }

    def _update_status(self) -> None:
        with self._lock:
            self._status.safe_mode = self.safe.active
            self._status.safe_mode_reason = self.safe.reason
            self._status.watchdog_ok = self.watchdog.is_ok()
            self._status.n_ai_ok = len(self._last_sensors)
            self._status.n_ao_ok = len(self.ai.outputs)
            self._status.n_di_ok = 8
            self._status.n_do_ok = 8


def _cli():
    import argparse, json
    ap = argparse.ArgumentParser(description="ARHPP PLC Simulator")
    ap.add_argument("--hz", type=float, default=50.0)
    ap.add_argument("--duration", type=float, default=10.0)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s %(levelname)s %(message)s")
    sim = PLCSimulator(SimulatorConfig(rt_loop_hz=args.hz))
    last_log = [0.0]

    def cb(snapshot):
        now = time.time()
        if now - last_log[0] >= 1.0:
            last_log[0] = now
            s = snapshot["status"]
            chokes = snapshot["chokes"]
            sensors = snapshot["sensors"]
            print(f"[{s['cycle_count']:>6}] "
                    f"cycle={s['cycle_time_ms']:.2f} ms  "
                    f"SBP={sensors.get('AI-1', {}).get('value', 0):.1f}  "
                    f"ChokeA={chokes.get('CHOKE-A', {}).get('actual_pct', 0):.1f}%  "
                    f"Safe={s['safe_mode']}")

    sim.register_callback(cb)
    print(f"Starting PLC Sim at {args.hz} Hz for {args.duration}s")
    sim.start()
    time.sleep(args.duration)
    sim.stop()
    print("Done.")


if __name__ == "__main__":
    _cli()
