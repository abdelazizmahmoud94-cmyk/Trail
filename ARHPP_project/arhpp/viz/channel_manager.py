"""Channel Registry — central channel definitions."""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional


class ChannelType(str, Enum):
    ANALOG = "analog"
    DIGITAL = "digital"
    COUNTER = "counter"
    STRING = "string"


class ChannelCategory(str, Enum):
    DRILLING = "drilling"
    HYDRAULICS = "hydraulics"
    MUD = "mud"
    GAS = "gas"
    PRESSURE = "pressure"
    TEMPERATURE = "temperature"
    FLOW = "flow"
    PIT = "pit"
    CONTROL = "control"
    PWD = "pwd"
    COMPUTED = "computed"
    EVENT = "event"


@dataclass
class Channel:
    id: str
    label: str
    unit: str
    category: ChannelCategory = ChannelCategory.DRILLING
    type: ChannelType = ChannelType.ANALOG
    min_psi: float = 0.0
    max_psi: float = 1000.0
    color: str = "#38bdf8"
    chart_group: str = "default"
    priority: int = 50
    metric_unit: Optional[str] = None
    metric_factor: float = 1.0
    metric_min: float = 0.0
    metric_max: float = 1000.0
    is_critical: bool = False
    description: str = ""

    def convert_to_metric(self, value: float) -> float:
        return value * self.metric_factor

    def convert_from_metric(self, value: float) -> float:
        return value / self.metric_factor if self.metric_factor else value

    def to_dict(self) -> dict:
        d = asdict(self)
        d["category"] = self.category.value
        d["type"] = self.type.value
        return d


def _ch(id_, label, unit, cat, min_v, max_v, color,
        priority=50, critical=False, **kw) -> Channel:
    return Channel(id=id_, label=label, unit=unit, category=cat,
                    min_psi=min_v, max_psi=max_v, color=color,
                    priority=priority, is_critical=critical, **kw)


DEFAULT_CHANNELS: List[Channel] = [
    _ch("bit_depth_ft", "Bit Depth", "ft", ChannelCategory.DRILLING,
        0, 25000, "#38bdf8", 95, True,
        metric_unit="m", metric_factor=0.3048,
        metric_min=0, metric_max=7620),
    _ch("rop_ft_hr", "ROP", "ft/hr", ChannelCategory.DRILLING,
        0, 200, "#f97316", 85, True,
        metric_unit="m/hr", metric_factor=0.3048,
        metric_min=0, metric_max=60),
    _ch("wob_klb", "WOB", "klb", ChannelCategory.DRILLING,
        0, 60, "#a78bfa", 80, True,
        metric_unit="kN", metric_factor=4.4482,
        metric_min=0, metric_max=270),
    _ch("rpm", "Rotary Speed", "rpm", ChannelCategory.DRILLING,
        0, 250, "#8b5cf6", 80, True),
    _ch("torque_ftlb", "Torque", "ft·lb", ChannelCategory.DRILLING,
        0, 40000, "#ec4899", 75, True,
        metric_unit="kN·m", metric_factor=0.00136,
        metric_min=0, metric_max=54),
    _ch("hookload_klb", "Hookload", "klb", ChannelCategory.DRILLING,
        0, 800, "#f43f5e", 70,
        metric_unit="kN", metric_factor=4.4482,
        metric_min=0, metric_max=3560),
    _ch("spp_psi", "Standpipe Pressure", "psi", ChannelCategory.HYDRAULICS,
        0, 7000, "#3b82f6", 90, True,
        metric_unit="kPa", metric_factor=6.895,
        metric_min=0, metric_max=48000),
    _ch("sbp_psi", "Surface Back Pressure", "psi", ChannelCategory.HYDRAULICS,
        0, 2000, "#fbbf24", 95, True,
        metric_unit="kPa", metric_factor=6.895,
        metric_min=0, metric_max=13800),
    _ch("wellhead_pressure_psi", "Wellhead Pressure", "psi",
        ChannelCategory.HYDRAULICS, 0, 5000, "#eab308", 85, True,
        metric_unit="kPa", metric_factor=6.895,
        metric_min=0, metric_max=34500),
    _ch("bhp_psi", "Bottom Hole Pressure", "psi", ChannelCategory.HYDRAULICS,
        0, 20000, "#06b6d4", 98, True,
        metric_unit="kPa", metric_factor=6.895,
        metric_min=0, metric_max=138000),
    _ch("ecd_ppg", "ECD", "ppg", ChannelCategory.HYDRAULICS,
        8, 20, "#10b981", 95, True,
        metric_unit="kg/m³", metric_factor=119.83,
        metric_min=960, metric_max=2400),
    _ch("esd_ppg", "ESD", "ppg", ChannelCategory.HYDRAULICS,
        8, 20, "#14b8a6", 85, True,
        metric_unit="kg/m³", metric_factor=119.83,
        metric_min=960, metric_max=2400),
    _ch("q_in_gpm", "Flow In", "gpm", ChannelCategory.FLOW,
        0, 1200, "#f472b6", 90, True,
        metric_unit="lpm", metric_factor=3.785,
        metric_min=0, metric_max=4500),
    _ch("q_out_gpm", "Flow Out", "gpm", ChannelCategory.FLOW,
        0, 1200, "#ef4444", 90, True,
        metric_unit="lpm", metric_factor=3.785,
        metric_min=0, metric_max=4500),
    _ch("q_effective_gpm", "Q Effective", "gpm", ChannelCategory.FLOW,
        0, 1200, "#06b6d4", 75,
        metric_unit="lpm", metric_factor=3.785,
        metric_min=0, metric_max=4500),
    _ch("q_utube_gpm", "Q U-Tube", "gpm", ChannelCategory.FLOW,
        -50, 50, "#a855f7", 60,
        metric_unit="lpm", metric_factor=3.785,
        metric_min=-190, metric_max=190),
    _ch("q_loss_gpm", "Q Loss", "gpm", ChannelCategory.FLOW,
        0, 500, "#dc2626", 70,
        metric_unit="lpm", metric_factor=3.785,
        metric_min=0, metric_max=1900),
    _ch("mw_in_ppg", "MW In", "ppg", ChannelCategory.MUD,
        7, 20, "#22d3ee", 85, True,
        metric_unit="kg/m³", metric_factor=119.83,
        metric_min=840, metric_max=2400),
    _ch("mw_out_ppg", "MW Out", "ppg", ChannelCategory.MUD,
        7, 20, "#0ea5e9", 85, True,
        metric_unit="kg/m³", metric_factor=119.83,
        metric_min=840, metric_max=2400),
    _ch("temp_in_f", "Temp In", "°F", ChannelCategory.TEMPERATURE,
        50, 250, "#fb923c", 60),
    _ch("temp_out_f", "Temp Out", "°F", ChannelCategory.TEMPERATURE,
        50, 300, "#f97316", 65),
    _ch("gas_total", "Total Gas", "units", ChannelCategory.GAS,
        0, 500, "#10b981", 80, True),
    _ch("gas_bg", "Background Gas", "units", ChannelCategory.GAS,
        0, 200, "#22c55e", 70),
    _ch("gas_cg", "Connection Gas", "units", ChannelCategory.GAS,
        0, 200, "#eab308", 75),
    _ch("gas_tg", "Trip Gas", "units", ChannelCategory.GAS,
        0, 200, "#f59e0b", 70),
    _ch("pit_volume_bbl", "Pit Volume", "bbl", ChannelCategory.PIT,
        0, 5000, "#14b8a6", 80, True),
    _ch("pit_gain_bbl", "Pit Gain", "bbl", ChannelCategory.PIT,
        -50, 50, "#eab308", 85, True),
    _ch("pwd_bhp_psi", "PWD BHP", "psi", ChannelCategory.PWD,
        0, 20000, "#22d3ee", 95, True),
    _ch("pwd_ecd_ppg", "PWD ECD", "ppg", ChannelCategory.PWD,
        8, 20, "#10b981", 90, True),
    _ch("choke_a_pct", "Choke A Position", "%", ChannelCategory.CONTROL,
        0, 100, "#3b82f6", 75, True),
    _ch("choke_b_pct", "Choke B Position", "%", ChannelCategory.CONTROL,
        0, 100, "#60a5fa", 60),
    _ch("kick_probability", "Kick Probability", "%", ChannelCategory.EVENT,
        0, 100, "#ef4444", 95, True),
    _ch("loss_fraction_pct", "Loss Fraction", "%", ChannelCategory.EVENT,
        0, 100, "#f59e0b", 85),
    _ch("confidence_pct", "Confidence", "%", ChannelCategory.COMPUTED,
        0, 100, "#10b981", 85, True),
]


class ChannelManager:
    def __init__(self):
        self._channels: Dict[str, Channel] = {}
        for ch in DEFAULT_CHANNELS:
            self._channels[ch.id] = ch

    def register(self, ch: Channel) -> None:
        self._channels[ch.id] = ch

    def get(self, channel_id: str) -> Optional[Channel]:
        return self._channels.get(channel_id)

    def list_all(self) -> List[Channel]:
        return list(self._channels.values())

    def list_by_category(self, cat: ChannelCategory) -> List[Channel]:
        return [c for c in self._channels.values() if c.category == cat]

    def list_critical(self) -> List[Channel]:
        return [c for c in self._channels.values() if c.is_critical]

    def get_by_id_list(self, ids: List[str]) -> List[Channel]:
        return [self._channels[i] for i in ids if i in self._channels]

    def to_dict_list(self) -> List[dict]:
        return [c.to_dict() for c in self._channels.values()]

    def stats(self) -> dict:
        return {
            "total": len(self._channels),
            "critical": len(self.list_critical()),
            "by_category": {cat.value: len(self.list_by_category(cat))
                              for cat in ChannelCategory},
        }


_manager: Optional[ChannelManager] = None


def get_channel_manager() -> ChannelManager:
    global _manager
    if _manager is None:
        _manager = ChannelManager()
    return _manager
