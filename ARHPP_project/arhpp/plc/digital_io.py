"""Digital I/O (16 lines)."""

import time
from typing import Dict

from arhpp.plc.types import (
    DIGITAL_INPUT_NAMES, DIGITAL_OUTPUT_NAMES,
)


class DigitalIO:
    def __init__(self):
        self._di = {n: False for n in DIGITAL_INPUT_NAMES}
        self._do = {n: False for n in DIGITAL_OUTPUT_NAMES}
        self._di_change_ts: Dict[str, float] = {}
        self._do_change_ts: Dict[str, float] = {}

    def set_input(self, name: str, value: bool) -> None:
        if name in self._di and self._di[name] != value:
            self._di[name] = value
            self._di_change_ts[name] = time.time()

    def read_input(self, name: str) -> bool:
        return self._di.get(name, False)

    def read_all_inputs(self) -> Dict[str, bool]:
        return dict(self._di)

    def set_output(self, name: str, value: bool) -> None:
        if name in self._do and self._do[name] != value:
            self._do[name] = value
            self._do_change_ts[name] = time.time()

    def read_output(self, name: str) -> bool:
        return self._do.get(name, False)

    def read_all_outputs(self) -> Dict[str, bool]:
        return dict(self._do)

    def di_bitfield(self) -> int:
        v = 0
        for i, n in enumerate(DIGITAL_INPUT_NAMES):
            if self._di.get(n):
                v |= (1 << i)
        return v

    def do_bitfield(self) -> int:
        v = 0
        for i, n in enumerate(DIGITAL_OUTPUT_NAMES):
            if self._do.get(n):
                v |= (1 << i)
        return v

    def any_pump_running(self) -> bool:
        return (self._di.get("MAIN_PUMP_1_RUNNING", False)
                 or self._di.get("MAIN_PUMP_2_RUNNING", False)
                 or self._di.get("AUX_PUMP_RUNNING", False))

    def esd_active(self) -> bool:
        return self._di.get("ESD_ACTIVE", False)

    def rcd_closed(self) -> bool:
        return self._di.get("RCD_CLOSED", False)
