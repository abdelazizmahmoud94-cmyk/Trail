"""Calibration Context — ContextVar for isolated parameters.

Usage:
    from arhpp.calibration.context import param_context, get_param

    # Live: no context -> uses defaults
    ecc = get_param("ecc_a")  # -> 0.072

    # Sandbox: with context -> uses profile
    with param_context(profile):
        ecc = get_param("ecc_a")  # -> value from profile

    # After exit: back to defaults
"""

from contextvars import ContextVar
from contextlib import contextmanager
from typing import Optional, Dict, Iterator


_current_profile: ContextVar[Optional[object]] = ContextVar(
    "current_calibration_profile", default=None)
_current_context_name: ContextVar[str] = ContextVar(
    "current_calibration_context", default="LIVE")


@contextmanager
def param_context(profile, context_name: str = "SANDBOX") -> Iterator[None]:
    """Activate a profile temporarily. Thread-safe via ContextVar."""
    token_p = _current_profile.set(profile)
    token_n = _current_context_name.set(context_name)
    try:
        yield
    finally:
        _current_profile.reset(token_p)
        _current_context_name.reset(token_n)


def get_param(name: str, default: Optional[float] = None) -> float:
    """Return parameter from current context, else default from REGISTRY."""
    profile = _current_profile.get()
    if profile is not None:
        values = getattr(profile, "values", None)
        if values is not None and name in values:
            return values[name]
    from arhpp.calibration.params import REGISTRY_BY_NAME
    spec = REGISTRY_BY_NAME.get(name)
    if spec is not None:
        return spec.default
    if default is not None:
        return default
    raise KeyError(f"Unknown param: {name}")


def get_all_params() -> Dict[str, float]:
    profile = _current_profile.get()
    if profile is not None:
        values = getattr(profile, "values", None)
        if values is not None:
            return dict(values)
    from arhpp.calibration.params import default_values
    return default_values()


def get_context_name() -> str:
    return _current_context_name.get()


def get_active_profile():
    return _current_profile.get()


def is_live() -> bool:
    return _current_profile.get() is None


def live_context():
    return param_context(None, context_name="LIVE")


def sandbox_context(profile, name: str = "SANDBOX"):
    return param_context(profile, context_name=name)
