"""DEPRECATED — use library.py instead.

Kept for backward compatibility with legacy code.
"""

import warnings
from pathlib import Path
from typing import Dict, Optional

from arhpp.calibration.library import get_library
from arhpp.calibration.profile import CalibrationProfile
from arhpp.calibration.params import default_values


DEFAULT_PATH = (Path(__file__).resolve().parent.parent.parent
                / "calibration.json")
_WARNED = {"save": False, "load": False, "describe": False}


def _warn_once(key: str, msg: str):
    if not _WARNED[key]:
        warnings.warn(msg, DeprecationWarning, stacklevel=3)
        _WARNED[key] = True


def save(values: Dict[str, float],
          path: Optional[Path] = None,
          metadata: Optional[dict] = None) -> Path:
    """DEPRECATED — use ProfileLibrary.save()."""
    _warn_once("save",
                "persist.save() is deprecated. Use ProfileLibrary.save().")
    profile = CalibrationProfile(
        name=(metadata or {}).get("name", "Legacy Profile"),
        description=(metadata or {}).get("description", ""),
        values=values,
        metadata=metadata or {},
    )
    lib = get_library()
    return lib.save(profile)


def load(path: Optional[Path] = None) -> Dict[str, float]:
    """
    DEPRECATED — always returns defaults to protect Live System.
    """
    _warn_once("load",
                "persist.load() is deprecated and returns defaults.")
    return default_values()


def describe(path: Optional[Path] = None) -> str:
    """DEPRECATED — use ProfileLibrary.list_profiles()."""
    _warn_once("describe", "persist.describe() is deprecated.")
    lib = get_library()
    profiles = lib.list_profiles()
    lines = ["Calibration Profiles (from library):", ""]
    for p in profiles:
        lines.append(f"  {p['id']:10s}  {p['name'][:30]:30s}  "
                       f"({p['n_changed']} changes)")
    if not profiles:
        lines.append("  (no profiles - using system defaults)")
    return "\n".join(lines)


def is_legacy_mode() -> bool:
    return False
