"""WITS legacy adapter — reads WITS records from a file."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from arhpp.sensors.base import SensorAdapter, SensorReading


WITS_MAP = {
    "0108": "md_ft", "0110": "bit_md_ft", "0118": "rop_ft_hr",
    "0120": "rpm", "0122": "wob_klb", "0124": "torque_ftlb",
    "0128": "spp_psi", "0130": "q_in_gpm", "0132": "q_out_gpm",
    "0134": "sbp_psi", "0136": "choke_position_pct",
    "0140": "mw_in_ppg", "0142": "mw_out_ppg",
    "0144": "temp_in_f", "0146": "temp_out_f",
    "0148": "total_gas_units", "0150": "background_gas_units",
    "0152": "connection_gas_units", "0154": "trip_gas_units",
    "0156": "pump_off_gas_units", "0158": "pit_volume_bbl",
}


class WITSFileAdapter(SensorAdapter):
    def __init__(self, path):
        self.path = Path(path)
        self._connected = False
        self._lines = []
        self._idx = 0

    def connect(self):
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        self._lines = self.path.read_text(
            encoding="utf-8", errors="ignore").splitlines()
        self._idx = 0
        self._connected = True

    def disconnect(self):
        self._connected = False

    def is_connected(self):
        return self._connected

    def _parse_line(self, line: str) -> Dict[str, float]:
        out = {}
        for m in re.finditer(r"(\d{4})\s*[:=]\s*([-\d\.]+)", line):
            field = WITS_MAP.get(m.group(1))
            if field:
                try:
                    out[field] = float(m.group(2))
                except ValueError:
                    pass
        return out

    def read(self):
        if not self._connected or self._idx >= len(self._lines):
            return None
        line = self._lines[self._idx]
        self._idx += 1
        if not line.strip():
            return None
        fields = self._parse_line(line)
        if not fields:
            return None
        return SensorReading(timestamp=datetime.utcnow(), **fields)
