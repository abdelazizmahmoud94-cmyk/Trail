"""Analog Input/Output channels with filtering, noise, calibration."""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from arhpp.plc.types import (
    SensorValue, PLCChannelSpec, SignalQuality,
    ANALOG_INPUT_SPECS, ANALOG_OUTPUT_SPECS,
)


@dataclass
class AnalogInput:
    spec: PLCChannelSpec
    scale: float = 1.0
    offset: float = 0.0
    invert: bool = False
    _last_raw: float = 0.0
    _filtered: float = 0.0
    _last_ts: float = field(default_factory=time.time)
    _fault: bool = False
    _stuck_counter: int = 0

    def set_process_value(self, value: float) -> None:
        self._last_raw = value

    def read(self, dt_s: float = 0.01) -> SensorValue:
        fs = self.spec.max_value - self.spec.min_value
        n_levels = 2 ** self.spec.resolution_bits
        step = fs / n_levels if n_levels > 0 else 0.0
        v = round(self._last_raw / step) * step if step > 0 else self._last_raw
        v = max(self.spec.min_value, min(self.spec.max_value, v))

        if self.spec.noise_sigma_pct > 0:
            sigma = (self.spec.noise_sigma_pct / 100.0) * fs
            v += random.gauss(0, sigma)

        alpha = self._alpha_from_tau(dt_s, self.spec.filter_cutoff_hz)
        self._filtered = alpha * v + (1 - alpha) * self._filtered

        value = self._filtered * self.scale + self.offset
        if self.invert:
            value = self.spec.max_value - value

        self._last_ts = time.time()
        return SensorValue(
            channel_id=self.spec.channel_id,
            value=value,
            unit=self.spec.unit,
            timestamp=self._last_ts,
            quality=self._quality(),
            raw_value=self._last_raw)

    @staticmethod
    def _alpha_from_tau(dt_s: float, cutoff_hz: float) -> float:
        if cutoff_hz <= 0 or dt_s <= 0:
            return 1.0
        tau = 1.0 / (2 * math.pi * cutoff_hz)
        return 1.0 - math.exp(-dt_s / tau)

    def _quality(self) -> SignalQuality:
        if self._fault:
            return SignalQuality.FAILED
        if self._last_raw < self.spec.min_value - 0.05 * (
                self.spec.max_value - self.spec.min_value):
            return SignalQuality.BAD
        return SignalQuality.GOOD

    def trigger_fault(self) -> None:
        self._fault = True

    def clear_fault(self) -> None:
        self._fault = False


@dataclass
class AnalogOutput:
    spec: PLCChannelSpec
    value: float = 0.0
    commanded: float = 0.0
    _last_update: float = field(default_factory=time.time)

    def set_command(self, value: float) -> None:
        self.commanded = max(self.spec.min_value,
                              min(self.spec.max_value, value))

    def update(self, dt_s: float) -> float:
        if self.spec.rate_limit_per_sec <= 0:
            self.value = self.commanded
        else:
            delta = self.commanded - self.value
            max_change = self.spec.rate_limit_per_sec * dt_s
            if abs(delta) > max_change:
                delta = max_change * (1 if delta > 0 else -1)
            self.value += delta
        n_levels = 2 ** self.spec.resolution_bits
        fs = self.spec.max_value - self.spec.min_value
        step = fs / n_levels if n_levels > 0 else 0
        if step > 0:
            self.value = round(self.value / step) * step
        self.value = max(self.spec.min_value,
                          min(self.spec.max_value, self.value))
        self._last_update = time.time()
        return self.value


class AnalogIOBank:
    def __init__(self):
        self.inputs: Dict[str, AnalogInput] = {
            s.channel_id: AnalogInput(spec=s) for s in ANALOG_INPUT_SPECS}
        self.outputs: Dict[str, AnalogOutput] = {
            s.channel_id: AnalogOutput(spec=s) for s in ANALOG_OUTPUT_SPECS}

    def set_input(self, channel_id: str, value: float) -> None:
        if channel_id in self.inputs:
            self.inputs[channel_id].set_process_value(value)

    def read_input(self, channel_id: str,
                     dt_s: float = 0.01) -> Optional[SensorValue]:
        ch = self.inputs.get(channel_id)
        return ch.read(dt_s) if ch else None

    def read_all_inputs(self, dt_s: float = 0.01) -> Dict[str, SensorValue]:
        return {cid: ch.read(dt_s) for cid, ch in self.inputs.items()}

    def inject_input_fault(self, channel_id: str) -> None:
        if channel_id in self.inputs:
            self.inputs[channel_id].trigger_fault()

    def clear_input_fault(self, channel_id: str) -> None:
        if channel_id in self.inputs:
            self.inputs[channel_id].clear_fault()

    def set_output(self, channel_id: str, value: float) -> None:
        if channel_id in self.outputs:
            self.outputs[channel_id].set_command(value)

    def update_outputs(self, dt_s: float) -> Dict[str, float]:
        return {cid: ch.update(dt_s) for cid, ch in self.outputs.items()}

    def get_output(self, channel_id: str) -> Optional[float]:
        ch = self.outputs.get(channel_id)
        return ch.value if ch else None
