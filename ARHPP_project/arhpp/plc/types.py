"""Data types for PLC Simulator."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class ControlMode(str, Enum):
    MANUAL = "MANUAL"
    COMPUTER = "COMPUTER"
    AP = "AP"
    SAFE = "SAFE"
    OFFLINE = "OFFLINE"


class ChokeState(str, Enum):
    IDLE = "IDLE"
    OPENING = "OPENING"
    CLOSING = "CLOSING"
    HOLDING = "HOLDING"
    FAULT = "FAULT"


class SafeModeReason(str, Enum):
    NONE = "NONE"
    WATCHDOG_TIMEOUT = "WATCHDOG_TIMEOUT"
    ESD_SIGNAL = "ESD_SIGNAL"
    SOFTWARE_CRASH = "SOFTWARE_CRASH"
    MANUAL_TRIGGER = "MANUAL_TRIGGER"
    NETWORK_LOST = "NETWORK_LOST"
    SENSOR_FAILURE = "SENSOR_FAILURE"


class SignalQuality(str, Enum):
    GOOD = "GOOD"
    UNCERTAIN = "UNCERTAIN"
    BAD = "BAD"
    FAILED = "FAILED"


class KickState(str, Enum):
    DISARMED = "DISARMED"
    ARMED = "ARMED"
    DETECTED = "DETECTED"
    PRESSURING = "PRESSURING"
    STABILIZING = "STABILIZING"
    SUCCESS = "SUCCESS"
    ESCALATED = "ESCALATED"
    RECOVERING = "RECOVERING"


@dataclass
class SensorValue:
    channel_id: str
    value: float = 0.0
    unit: str = "psi"
    timestamp: float = 0.0
    quality: SignalQuality = SignalQuality.GOOD
    raw_value: float = 0.0
    noise_applied: float = 0.0


@dataclass
class ChokeCommand:
    choke_id: str
    position_pct: float = 0.0
    mode: ControlMode = ControlMode.MANUAL
    setpoint_psi: float = 0.0
    timestamp: float = 0.0
    source: str = "operator"


@dataclass
class ChokeFeedback:
    choke_id: str
    commanded_pct: float = 0.0
    actual_pct: float = 0.0
    rate_pct_sec: float = 0.0
    is_moving: bool = False
    state: ChokeState = ChokeState.IDLE
    upstream_pressure_psi: float = 0.0
    downstream_pressure_psi: float = 0.0
    flow_gpm: float = 0.0


@dataclass
class PLCStatus:
    model: str = "cRIO-9031 (SIM)"
    ip: str = "192.168.79.100"
    firmware: str = "1.0.46-SIM"
    serial: str = "SIM-00000000"
    cpu_load_pct: float = 0.0
    cycle_time_ms: float = 0.0
    target_cycle_ms: float = 10.0
    watchdog_ok: bool = True
    watchdog_last_update: float = 0.0
    safe_mode: bool = False
    safe_mode_reason: SafeModeReason = SafeModeReason.NONE
    uptime_sec: float = 0.0
    start_time: Optional[datetime] = None
    n_ai_ok: int = 0
    n_ai_total: int = 4
    n_ao_ok: int = 0
    n_ao_total: int = 4
    n_di_ok: int = 0
    n_di_total: int = 8
    n_do_ok: int = 0
    n_do_total: int = 8
    cycle_count: int = 0
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["safe_mode_reason"] = (self.safe_mode_reason.value if hasattr(self.safe_mode_reason, "value") else str(self.safe_mode_reason))
        d["start_time"] = (self.start_time.isoformat() if hasattr(self.start_time, "isoformat") else (str(self.start_time) if self.start_time else None))
        return d


@dataclass
class PLCChannelSpec:
    channel_id: str
    name: str
    unit: str
    min_value: float
    max_value: float
    default: float = 0.0
    resolution_bits: int = 16
    filter_cutoff_hz: float = 2.0
    noise_sigma_pct: float = 0.5
    rate_limit_per_sec: float = 0.0
    deadband: float = 0.0
    description: str = ""


ANALOG_INPUT_SPECS = [
    PLCChannelSpec("AI-0", "SPP", "psi", 0.0, 10000.0, 16, 2.0, 0.5, 0, 0,
                    "Standpipe Pressure"),
    PLCChannelSpec("AI-1", "SBP", "psi", 0.0, 3000.0, 16, 2.0, 0.5, 0, 0,
                    "Surface Back Pressure"),
    PLCChannelSpec("AI-2", "Wellhead Pressure", "psi", 0.0, 5000.0, 16, 2.0, 0.5, 0, 0,
                    "Wellhead Pressure"),
    PLCChannelSpec("AI-3", "PWD BHP", "psi", 0.0, 20000.0, 16, 2.0, 0.3, 0, 0,
                    "Pressure While Drilling BHP"),
]


ANALOG_OUTPUT_SPECS = [
    PLCChannelSpec("AO-0", "Choke A Position", "%", 0.0, 100.0, 12, 0, 0, 5.0, 0.1,
                    "Choke A Command"),
    PLCChannelSpec("AO-1", "Choke B Position", "%", 0.0, 100.0, 12, 0, 0, 5.0, 0.1,
                    "Choke B Command"),
    PLCChannelSpec("AO-2", "Aux Pump Rate", "spm", 0.0, 150.0, 12, 0, 0, 20.0, 0,
                    "Aux Pump Stroke Rate"),
    PLCChannelSpec("AO-3", "Spare", "%", 0.0, 100.0, 12, 0, 0, 0, 0, "Spare"),
]


DIGITAL_INPUT_NAMES = [
    "MAIN_PUMP_1_RUNNING", "MAIN_PUMP_2_RUNNING", "AUX_PUMP_RUNNING",
    "CHOKE_A_AUTO", "CHOKE_B_AUTO", "RCD_CLOSED", "ESD_ACTIVE", "SPARE_DI",
]


DIGITAL_OUTPUT_NAMES = [
    "PUMP_1_START", "PUMP_2_START", "AUX_PUMP_START",
    "CHOKE_A_ENABLE", "CHOKE_B_ENABLE", "ALARM_BEACON", "ALARM_HORN", "SPARE_DO",
]


CHOKE_CV_CURVE = [
    (0.0, 0.00), (10.0, 0.02), (20.0, 0.06), (30.0, 0.15),
    (40.0, 0.28), (50.0, 0.45), (60.0, 0.62), (70.0, 0.78),
    (80.0, 0.90), (90.0, 0.97), (100.0, 1.00),
]
