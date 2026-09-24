"""Calibration Sandbox — fully isolated environment."""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Callable, Dict

from arhpp.calibration.profile import (
    CalibrationProfile, default_profile,
)
from arhpp.calibration.context import sandbox_context
from arhpp.calibration.targets import WellTarget


@dataclass
class SandboxRun:
    run_id: str
    profile: CalibrationProfile
    wells: list
    well_targets: List = field(default_factory=list)
    overall_score: float = 0.0
    duration_s: float = 0.0
    started_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat())
    notes: str = ""


@dataclass
class SandboxComparison:
    runs: List[SandboxRun] = field(default_factory=list)

    def best_run(self) -> Optional[SandboxRun]:
        if not self.runs:
            return None
        return min(self.runs, key=lambda r: r.overall_score)

    def worst_run(self) -> Optional[SandboxRun]:
        if not self.runs:
            return None
        return max(self.runs, key=lambda r: r.overall_score)

    def to_table(self) -> List[dict]:
        return [
            {
                "run_id": r.run_id,
                "profile": r.profile.name,
                "score": round(r.overall_score, 5),
                "n_wells": len(r.wells),
                "duration_s": round(r.duration_s, 2),
            }
            for r in self.runs
        ]


class CalibrationSandbox:
    """Isolated sandbox for calibration experiments."""

    def __init__(self):
        self.wells = []
        self.runs: List[SandboxRun] = []
        self._run_counter = 0

    def load_wells(self, wells) -> None:
        self.wells = list(wells)

    def add_well(self, well) -> None:
        self.wells.append(well)

    def clear_wells(self) -> None:
        self.wells = []

    def list_wells_summary(self) -> List[dict]:
        return [
            {
                "well_id": w.well_id,
                "formation": w.formation,
                "md_ft": w.md_ft,
                "mw_ppg": w.mw_in_ppg,
                "has_pwd": w.pwd_bhp_psi is not None,
                "has_spp": w.spp_measured_psi is not None,
                "had_kick": w.had_kick,
                "had_losses": w.had_losses,
            }
            for w in self.wells
        ]

    def evaluate(self, profile: CalibrationProfile,
                  notes: str = "",
                  progress_cb: Optional[Callable] = None) -> SandboxRun:
        if not self.wells:
            raise ValueError("No wells loaded. Use load_wells() first.")

        self._run_counter += 1
        run_id = f"RUN-{self._run_counter:04d}"
        t0 = time.time()
        well_targets: List[WellTarget] = []

        from arhpp.calibration.objective import run_well_evaluation

        with sandbox_context(profile, context_name=run_id):
            for i, well in enumerate(self.wells):
                try:
                    target = run_well_evaluation(well)
                    well_targets.append(target)
                except Exception:
                    t = WellTarget(well_id=well.well_id)
                    t.composite = 1.0
                    well_targets.append(t)
                if progress_cb:
                    progress_cb(i + 1, well.well_id)

        if well_targets:
            score = sum(t.composite for t in well_targets) / len(well_targets)
        else:
            score = 0.0

        duration = time.time() - t0
        run = SandboxRun(
            run_id=run_id, profile=profile, wells=list(self.wells),
            well_targets=well_targets, overall_score=score,
            duration_s=duration, notes=notes)
        self.runs.append(run)
        return run

    def compare(self, runs=None) -> SandboxComparison:
        return SandboxComparison(runs=runs or self.runs)

    def best_run(self) -> Optional[SandboxRun]:
        if not self.runs:
            return None
        return min(self.runs, key=lambda r: r.overall_score)

    def clear_runs(self) -> None:
        self.runs = []

    def reset(self) -> None:
        self.wells = []
        self.runs = []
        self._run_counter = 0

    def summary(self) -> dict:
        return {
            "n_wells": len(self.wells),
            "n_runs": len(self.runs),
            "best_score": (min(r.overall_score for r in self.runs)
                            if self.runs else None),
            "wells": self.list_wells_summary(),
        }
