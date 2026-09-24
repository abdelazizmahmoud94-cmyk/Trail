"""Aggregate all event detectors into one report."""

from dataclasses import dataclass, field

from arhpp.events.kick import KickInputs, KickResult, compute_kick
from arhpp.events.nozzle_plug import (
    NozzlePlugResult, compute_nozzle_plug,
)
from arhpp.events.bit_balling import (
    BitBallingInputs, BitBallingResult, compute_bit_balling,
)
from arhpp.events.packoff import (
    PackOffInputs, PackOffResult, compute_packoff,
)
from arhpp.events.washout import (
    WashoutInputs, WashoutResult, compute_washout,
)


@dataclass
class EventsInputs:
    kick: KickInputs = field(default_factory=KickInputs)
    bit_balling: BitBallingInputs = field(default_factory=BitBallingInputs)
    packoff: PackOffInputs = field(default_factory=PackOffInputs)
    washout: WashoutInputs = field(default_factory=WashoutInputs)
    kick_duration_min: float = 0.0
    expected_bit_dp_psi: float = 0.0
    actual_bit_dp_psi: float = 0.0
    tfa_expected_in2: float = 0.0
    cd: float = 0.95


@dataclass
class EventsResult:
    kick: KickResult = field(default_factory=KickResult)
    nozzle: NozzlePlugResult = field(default_factory=NozzlePlugResult)
    balling: BitBallingResult = field(default_factory=BitBallingResult)
    packoff: PackOffResult = field(default_factory=PackOffResult)
    washout: WashoutResult = field(default_factory=WashoutResult)
    overall_risk: str = "none"
    n_alerts: int = 0


def compute_events(inp: EventsInputs) -> EventsResult:
    r = EventsResult()
    r.kick = compute_kick(inp.kick, kick_duration_min=inp.kick_duration_min)
    r.nozzle = compute_nozzle_plug(
        expected_dp_psi=inp.expected_bit_dp_psi,
        actual_dp_psi=inp.actual_bit_dp_psi,
        q_gpm=inp.kick.q_in_gpm,
        mw_ppg=inp.kick.mw_ppg,
        tfa_expected_in2=inp.tfa_expected_in2,
        cd=inp.cd)
    r.balling = compute_bit_balling(inp.bit_balling)
    r.packoff = compute_packoff(inp.packoff)
    r.washout = compute_washout(inp.washout)

    sev = []
    if r.kick.severity in ("severe", "blowout-risk"):
        sev.append("high")
    if r.nozzle.risk in ("moderate", "severe"):
        sev.append("moderate")
    if r.balling.risk in ("moderate", "high"):
        sev.append("moderate")
    if r.packoff.risk in ("moderate", "high"):
        sev.append("high")
    if r.washout.risk in ("moderate", "high"):
        sev.append("moderate")

    if "high" in sev:
        r.overall_risk = "high"
    elif "moderate" in sev:
        r.overall_risk = "moderate"
    elif sev:
        r.overall_risk = "low"
    else:
        r.overall_risk = "none"

    r.n_alerts = sum([
        1 if r.kick.severity not in ("none", "minor") else 0,
        1 if r.nozzle.is_flagged else 0,
        1 if r.balling.risk not in ("none", "low") else 0,
        1 if r.packoff.risk not in ("none", "low") else 0,
        1 if r.washout.risk not in ("none", "low") else 0,
    ])
    return r
