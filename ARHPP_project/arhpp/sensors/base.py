"""Abstract base for all sensor adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict


@dataclass
class SensorReading:
    timestamp: datetime
    md_ft: float = 0.0
    bit_md_ft: float = 0.0
    rop_ft_hr: float = 0.0
    rpm: float = 0.0
    wob_klb: float = 0.0
    torque_ftlb: float = 0.0
    spp_psi: float = 0.0
    q_in_gpm: float = 0.0
    q_out_gpm: float = 0.0
    pit_volume_bbl: float = 0.0
    sbp_psi: float = 0.0
    choke_position_pct: float = 0.0
    mw_in_ppg: float = 0.0
    mw_out_ppg: float = 0.0
    temp_in_f: float = 0.0
    temp_out_f: float = 0.0
    total_gas_units: float = 0.0
    background_gas_units: float = 0.0
    connection_gas_units: float = 0.0
    trip_gas_units: float = 0.0
    pump_off_gas_units: float = 0.0
    pumps_on: bool = True
    connection: bool = False
    trip_mode: str = "static"
    pwd_bhp_psi: Optional[float] = None
    pwd_annular_pressure_psi: Optional[float] = None
    pwd_ecd_ppg: Optional[float] = None
    pwd_temp_f: Optional[float] = None
    extra: Dict[str, float] = field(default_factory=dict)


class SensorAdapter(ABC):
    @abstractmethod
    def connect(self) -> None: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def read(self) -> Optional[SensorReading]: ...
    @abstractmethod
    def is_connected(self) -> bool: ...

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.disconnect()
