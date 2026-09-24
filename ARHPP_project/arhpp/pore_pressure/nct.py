"""Normal Compaction Trend (NCT) fitting."""

import math
from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class NCTFit:
    a: float = 1.0
    b: float = 5e-4
    c: float = 0.0
    r_squared: float = 0.0
    n_points: int = 0
    is_fitted: bool = False


def fit_nct_exponential(tvds: List[float], values: List[float],
                          method: str = "log-linear") -> NCTFit:
    """
    Fit V(TVD) = a * exp(-b * TVD) + c
    Default: log-linear (c=0).
    """
    fit = NCTFit()
    if len(tvds) < 3 or len(values) != len(tvds):
        return fit

    t = np.array(tvds, dtype=float)
    v = np.array(values, dtype=float)

    mask = np.isfinite(t) & np.isfinite(v) & (v > 0)
    t = t[mask]
    v = v[mask]
    if len(t) < 3:
        return fit

    if method == "log-linear":
        ln_v = np.log(v)
        A = np.vstack([np.ones_like(t), -t]).T
        coef, *_ = np.linalg.lstsq(A, ln_v, rcond=None)
        ln_a, b = coef
        a = math.exp(ln_a)
        pred = a * np.exp(-b * t)
        ssr = float(np.sum((v - pred) ** 2))
        sst = float(np.sum((v - v.mean()) ** 2))
        fit.a = a
        fit.b = b
        fit.c = 0.0
        fit.r_squared = 1.0 - ssr / sst if sst > 0 else 0.0
        fit.n_points = len(t)
        fit.is_fitted = True
        return fit

    # General 3-param
    try:
        from scipy.optimize import curve_fit

        def model(t, a, b, c):
            return a * np.exp(-b * t) + c

        p0 = [float(v.max()), 5e-4, float(v.min()) * 0.5]
        bounds = ([0.0, 1e-6, -10.0], [100.0, 1e-2, 10.0])
        popt, _ = curve_fit(model, t, v, p0=p0,
                              bounds=bounds, maxfev=20000)
        pred = model(t, *popt)
        ssr = float(np.sum((v - pred) ** 2))
        sst = float(np.sum((v - v.mean()) ** 2))
        fit.a = float(popt[0])
        fit.b = float(popt[1])
        fit.c = float(popt[2])
        fit.r_squared = 1.0 - ssr / sst if sst > 0 else 0.0
        fit.n_points = len(t)
        fit.is_fitted = True
    except Exception:
        pass
    return fit


def evaluate_nct(fit: NCTFit, tvd_ft: float) -> float:
    if not fit.is_fitted:
        return 0.0
    return fit.a * math.exp(-fit.b * tvd_ft) + fit.c
