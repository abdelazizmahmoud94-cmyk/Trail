"""Ballooning Engine — distinguish Formation Breathing from Kick."""

from dataclasses import dataclass
from typing import List

from arhpp.core.constants import BALLOONING_PIT_GAIN_BBL


@dataclass
class PitEvent:
    time_min: float
    pit_gain_bbl: float
    q_out_gpm: float = 0.0
    connection_made: bool = False
    pumps_off: bool = False


@dataclass
class BallooningResult:
    classification: str = "unknown"
    confidence: float = 0.0
    max_pit_gain_bbl: float = 0.0
    gain_duration_min: float = 0.0
    decays_after_pumps_off: bool = False
    happens_on_connection: bool = False
    q_out_excess_gpm: float = 0.0


def classify_pit_event(events: List[PitEvent]) -> BallooningResult:
    """
    Decision rules:
      - Kick: pit gain monotonic, does NOT decay after pumps-off,
              Q_out > Q_in when pumps off.
      - Ballooning: pit gain after connection, decays after pumps off.
      - Loss: pit loss (negative gain).
    """
    r = BallooningResult()
    if not events:
        return r

    gains = [e.pit_gain_bbl for e in events]
    r.max_pit_gain_bbl = max(gains + [0.0])
    r.gain_duration_min = events[-1].time_min - events[0].time_min

    off = [e for e in events if e.pumps_off]
    if len(off) >= 2:
        r.decays_after_pumps_off = (
            off[-1].pit_gain_bbl < off[0].pit_gain_bbl * 0.7)
    r.happens_on_connection = any(e.connection_made for e in events)

    ex = [e.q_out_gpm for e in events if e.pumps_off and e.q_out_gpm > 0]
    if ex:
        r.q_out_excess_gpm = sum(ex) / len(ex)

    if r.max_pit_gain_bbl < BALLOONING_PIT_GAIN_BBL:
        r.classification = "normal"
        r.confidence = 0.9
        return r

    if (r.happens_on_connection and r.decays_after_pumps_off
            and r.q_out_excess_gpm < 20):
        r.classification = "ballooning"
        r.confidence = 0.85
        return r

    if (not r.decays_after_pumps_off
            and r.q_out_excess_gpm > 30):
        r.classification = "kick"
        r.confidence = 0.9
        return r

    r.classification = "ambiguous"
    r.confidence = 0.5
    return r
