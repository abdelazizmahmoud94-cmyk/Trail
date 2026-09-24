"""Calibration Optimizer — works in isolated sandbox."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable

from arhpp.calibration.params import (
    REGISTRY, default_values, clamp_values, normalize_pp_weights,
)
from arhpp.calibration.objective import objective, evaluate_all
from arhpp.calibration.profile import CalibrationProfile


@dataclass
class OptimizerResult:
    best_profile: CalibrationProfile
    best_score: float
    initial_profile: CalibrationProfile
    initial_score: float
    improvement_pct: float
    n_iterations: int = 0
    history: List[tuple] = field(default_factory=list)
    well_targets: List = field(default_factory=list)
    stages: List[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "best_score": round(self.best_score, 6),
            "initial_score": round(self.initial_score, 6),
            "improvement_pct": round(self.improvement_pct, 2),
            "n_iterations": self.n_iterations,
            "best_profile_id": self.best_profile.id,
            "best_profile_name": self.best_profile.name,
            "n_params_changed": len(self.best_profile.diff_from_default()),
        }


def _grid_for(p) -> List[float]:
    mid = p.default
    return [
        p.clamp(mid - 0.25 * (mid - p.lo) if mid > p.lo else p.lo),
        p.clamp(mid),
        p.clamp(mid + 0.25 * (p.hi - mid) if mid < p.hi else p.hi),
    ]


def _choose_subset(registry, stage: int) -> List:
    groups = {
        1: ("rheology", "annular"),
        2: ("losses",),
        3: ("pp",),
        4: ("gas",),
        5: (),
    }
    allowed = groups.get(stage, None)
    if allowed is None:
        return list(registry)
    if not allowed:
        return []
    return [p for p in registry if p.category in allowed]


def calibrate(wells: List,
                base_profile: Optional[CalibrationProfile] = None,
                profile_name: str = "Calibrated",
                stages: tuple = (1, 2, 3, 4),
                refine: bool = True,
                progress_cb: Optional[Callable] = None) -> OptimizerResult:
    if base_profile is None:
        base_profile = CalibrationProfile(name="Default")
        initial = dict(default_values())
    else:
        initial = dict(base_profile.values)

    initial_score = objective(initial, wells)
    current = dict(initial)
    current_score = initial_score
    history = [(0, current_score, dict(current))]
    stages_desc = []
    n_iter = 0

    for stage in stages:
        subset = _choose_subset(REGISTRY, stage)
        if not subset:
            continue
        stages_desc.append(f"Stage {stage}: {[p.name for p in subset]}")
        improved = True
        rounds = 0
        while improved and rounds < 3:
            improved = False
            rounds += 1
            for p in subset:
                grid = _grid_for(p)
                best_v = current[p.name]
                best_s = current_score
                for v in grid:
                    trial = dict(current)
                    trial[p.name] = v
                    if stage == 3:
                        trial = normalize_pp_weights(trial)
                    trial = clamp_values(trial)
                    s = objective(trial, wells)
                    n_iter += 1
                    if s < best_s - 1e-6:
                        best_s = s
                        best_v = v
                        improved = True
                current[p.name] = best_v
                if stage == 3:
                    current = normalize_pp_weights(current)
                current = clamp_values(current)
                current_score = best_s
                history.append((n_iter, current_score, dict(current)))
                if progress_cb:
                    progress_cb(n_iter, current_score, current)

    if refine:
        try:
            from scipy.optimize import minimize
            import numpy as np

            names = [p.name for p in REGISTRY]
            x0 = np.array([current[n] for n in names], dtype=float)

            def wrap(x):
                vals = {n: float(v) for n, v in zip(names, x)}
                vals = normalize_pp_weights(vals)
                vals = clamp_values(vals)
                return objective(vals, wells)

            stages_desc.append("Nelder-Mead refinement")
            res = minimize(wrap, x0, method="Nelder-Mead",
                            options={"maxiter": 400, "xatol": 1e-4,
                                     "fatol": 1e-6, "disp": False})
            n_iter += int(res.nit)
            refined = {n: float(v) for n, v in zip(names, res.x)}
            refined = normalize_pp_weights(refined)
            refined = clamp_values(refined)
            refined_score = objective(refined, wells)
            if refined_score < current_score:
                current = refined
                current_score = refined_score
            history.append((n_iter, current_score, dict(current)))
        except Exception:
            stages_desc.append("Nelder-Mead skipped (scipy missing)")

    final_profile = CalibrationProfile(
        name=profile_name,
        description=f"Calibrated on {len(wells)} wells",
        values=current,
        metadata={
            "n_wells": len(wells),
            "initial_score": round(initial_score, 6),
            "final_score": round(current_score, 6),
        })

    well_targets = evaluate_all(current, wells)
    improvement = 0.0
    if initial_score > 0:
        improvement = 100.0 * (initial_score - current_score) / initial_score

    return OptimizerResult(
        best_profile=final_profile,
        best_score=current_score,
        initial_profile=base_profile,
        initial_score=initial_score,
        improvement_pct=improvement,
        n_iterations=n_iter,
        history=history,
        well_targets=well_targets,
        stages=stages_desc)
