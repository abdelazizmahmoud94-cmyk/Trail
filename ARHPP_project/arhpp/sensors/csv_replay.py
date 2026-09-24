"""CSV Replay Adapter – streams readings from a CSV file."""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from arhpp.sensors.base import SensorAdapter, SensorReading


def _f(row, k, d=0.0):
    v = row.get(k, "")
    if v is None or v == "":
        return d
    try:
        return float(v)
    except ValueError:
        return d


def _b(row, k):
    return str(row.get(k, "")).strip().upper() in (
        "TRUE", "1", "YES", "Y", "T")


class CSVReplayAdapter(SensorAdapter):
    def __init__(self, csv_path, start_time=None,
                 dt_seconds=1.0, loop=False):
        self.path = Path(csv_path)
        self.start_time = start_time or datetime.utcnow()
        self.dt = timedelta(seconds=dt_seconds)
        self.loop = loop
        self._rows = []
        self._idx = 0
        self._connected = False

    def connect(self):
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        with open(self.path, "r", encoding="utf-8") as f:
            self._rows = [dict(r) for r in csv.DictReader(f)]
        self._idx = 0
        self._connected = True

    def disconnect(self):
        self._connected = False

    def is_connected(self):
        return self._connected

    def read(self):
        if not self._connected or not self._rows:
            return None
        if self._idx >= len(self._rows):
            if self.loop:
                self._idx = 0
            else:
                return None
        row = self._rows[self._idx]
        ts = self.start_time + self.dt * self._idx
        self._idx += 1
        return SensorReading(
            timestamp=ts,
            md_ft=_f(row, "MD_ft"),
            bit_md_ft=_f(row, "Bit_MD_ft", _f(row, "MD_ft")),
            rop_ft_hr=_f(row, "ROP_ft_hr"),
            rpm=_f(row, "RPM"),
            wob_klb=_f(row, "WOB_klb"),
            torque_ftlb=_f(row, "Torque_ftlb"),
            spp_psi=_f(row, "SPP_psi"),
            q_in_gpm=_f(row, "Q_in_gpm"),
            q_out_gpm=_f(row, "Q_out_gpm"),
            pit_volume_bbl=_f(row, "Pit_Volume_bbl"),
            sbp_psi=_f(row, "SBP_psi"),
            choke_position_pct=_f(row, "Choke_pct"),
            mw_in_ppg=_f(row, "MW_in_ppg", 10.0),
            mw_out_ppg=_f(row, "MW_out_ppg", 10.0),
            temp_in_f=_f(row, "Temp_in_F", 90.0),
            temp_out_f=_f(row, "Temp_out_F", 120.0),
            total_gas_units=_f(row, "TotalGas_units"),
            background_gas_units=_f(row, "BG_units"),
            connection_gas_units=_f(row, "CG_units"),
            trip_gas_units=_f(row, "TG_units"),
            pump_off_gas_units=_f(row, "POG_units"),
            pumps_on=_b(row, "PumpsOn") if "PumpsOn" in row else True,
            connection=_b(row, "Connection"),
            trip_mode=(row.get("TripMode") or "static").lower(),
            pwd_bhp_psi=_f(row, "PWD_BHP_psi") or None,
            pwd_ecd_ppg=_f(row, "PWD_ECD_ppg") or None)
