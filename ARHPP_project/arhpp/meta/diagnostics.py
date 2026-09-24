"""Diagnostics Engine – full Pressure Ledger with ranked contributions."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional

from arhpp.core.types import PressureLedger


@dataclass
class LedgerTerm:
    label: str
    value_psi: float
    category: str
    sign: str
    fraction_of_bhp: float = 0.0
    comment: str = ""


@dataclass
class DiagnosticsReport:
    bhp_psi: float = 0.0
    ecd_ppg: float = 0.0
    tvd_ref_ft: float = 0.0
    terms: List[LedgerTerm] = field(default_factory=list)
    contributions_positive_psi: float = 0.0
    contributions_negative_psi: float = 0.0
    top_positive: List[LedgerTerm] = field(default_factory=list)
    top_negative: List[LedgerTerm] = field(default_factory=list)
    balance_residual_psi: float = 0.0
    is_balanced: bool = False


def _classify(label: str) -> str:
    if label in ("Hydrostatic (Annulus)", "SBP"):
        return "static"
    if label in ("Annular Friction", "Surge"):
        return "dynamic"
    if label in ("Swab", "Gas Effect", "Loss Effect", "Kick Effect"):
        return "event"
    return "other"


def build_diagnostics(ledger: PressureLedger,
                        spp_psi: Optional[float] = None,
                        notes: Optional[Dict[str, str]] = None
                        ) -> DiagnosticsReport:
    r = DiagnosticsReport(
        bhp_psi=ledger.bhp,
        ecd_ppg=ledger.ecd,
        tvd_ref_ft=ledger.tvd_ref,
    )
    notes = notes or {}

    raw_terms = [
        ("Hydrostatic (Annulus)", ledger.hydrostatic_annulus, "+"),
        ("Annular Friction", ledger.annular_friction, "+"),
        ("SBP", ledger.sbp, "+"),
        ("Surge", ledger.surge, "+"),
        ("Swab", -ledger.swab, "-"),
        ("Gas Effect", ledger.gas_effect, "-"),
        ("Loss Effect", ledger.loss_effect, "-"),
        ("Kick Effect", ledger.kick_effect, "-"),
        ("Hydrostatic (String)", ledger.hydrostatic_string, "ref"),
        ("Pipe Friction", ledger.pipe_friction, "ref"),
        ("Bit dP", ledger.bit_dp, "ref"),
        ("U-Tube dP", ledger.utube, "ref"),
    ]

    bhp_abs = max(abs(ledger.bhp), 1e-6)
    pos = 0.0
    neg = 0.0

    for label, value, sign in raw_terms:
        cat = "reference" if sign == "ref" else _classify(label)
        t = LedgerTerm(
            label=label, value_psi=value, category=cat, sign=sign,
            fraction_of_bhp=value / bhp_abs,
            comment=notes.get(label, ""),
        )
        if sign == "+" and value > 0:
            pos += value
        elif sign == "-" and value < 0:
            neg += value
        r.terms.append(t)

    effective = [t for t in r.terms if t.sign != "ref"]
    r.top_positive = sorted(
        [t for t in effective if t.value_psi > 0],
        key=lambda x: x.value_psi, reverse=True,
    )[:3]
    r.top_negative = sorted(
        [t for t in effective if t.value_psi < 0],
        key=lambda x: x.value_psi,
    )[:3]

    r.contributions_positive_psi = pos
    r.contributions_negative_psi = neg

    computed = pos + neg
    r.balance_residual_psi = computed - ledger.bhp
    r.is_balanced = abs(r.balance_residual_psi) < 1.0

    return r


def diagnostics_to_rows(report: DiagnosticsReport) -> List[dict]:
    return [
        {
            "Component": t.label,
            "Value_psi": round(t.value_psi, 3),
            "Sign": t.sign,
            "Category": t.category,
            "Fraction_of_BHP": round(t.fraction_of_bhp, 4),
            "Comment": t.comment,
        }
        for t in report.terms
    ]
