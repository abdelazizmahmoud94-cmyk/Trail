"""PLC Simulator — cRIO-9031/9042 + Chokes + Kick Auto."""
from arhpp.plc.types import (
    SensorValue, ChokeCommand, ChokeFeedback, PLCStatus,
    ControlMode, SafeModeReason, KickState, ChokeState,
    SignalQuality, PLCChannelSpec,
)
from arhpp.plc.choke import ChokeModel, compute_choke_flow
from arhpp.plc.analog_io import AnalogIOBank
from arhpp.plc.digital_io import DigitalIO
from arhpp.plc.control_modes import (
    PIDController, APController, ChokeModeManager,
)
from arhpp.plc.watchdog import Watchdog, SafeModeManager
from arhpp.plc.kick_auto import KickAutoController, KickAutoConfig
from arhpp.plc.simulator import PLCSimulator, SimulatorConfig, PhysicsSnapshot
__all__ = [
    "SensorValue", "ChokeCommand", "ChokeFeedback", "PLCStatus",
    "ControlMode", "SafeModeReason", "KickState", "ChokeState",
    "SignalQuality", "PLCChannelSpec",
    "ChokeModel", "compute_choke_flow",
    "AnalogIOBank", "DigitalIO",
    "PIDController", "APController", "ChokeModeManager",
    "Watchdog", "SafeModeManager",
    "KickAutoController", "KickAutoConfig",
    "PLCSimulator", "SimulatorConfig", "PhysicsSnapshot",
]
