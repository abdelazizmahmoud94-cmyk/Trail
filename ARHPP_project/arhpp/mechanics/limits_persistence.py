"""Persistence layer for mechanical operating-limit profiles."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from arhpp.mechanics.limits_config import (
    DEFAULT_LIMITS,
    LimitDirection,
    LimitsRegistry,
    ParameterLimit,
)


PROFILE_DIR = (
    Path(__file__).resolve().parents[2]
    / "limits_profiles"
)

DEFAULT_PROFILE_NAME = "Default"


def _safe_name(name: str) -> str:
    """Convert a profile name to a safe filename."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name).strip())
    cleaned = cleaned.strip("._")

    if not cleaned:
        raise ValueError("Profile name cannot be empty")

    return cleaned[:100]


def _profile_path(name: str) -> Path:
    """Return the JSON path for a named profile."""
    return PROFILE_DIR / f"{_safe_name(name)}.json"


def _limit_to_storage(limit: ParameterLimit) -> Dict[str, Any]:
    """Serialize only editable and persistent limit fields."""
    return {
        "param_name": limit.param_name,
        "display_name": limit.display_name,
        "unit": limit.unit,
        "normal_min": float(limit.normal_min),
        "normal_max": float(limit.normal_max),
        "warning_pct": float(limit.warning_pct),
        "critical_pct": float(limit.critical_pct),
        "direction": limit.direction.value,
        "event_type_name": limit.event_type_name,
    }


def _limit_from_storage(
    param_name: str,
    data: Dict[str, Any],
) -> ParameterLimit:
    """Deserialize one ParameterLimit with defensive defaults."""
    direction_raw = data.get("direction", "high")

    try:
        direction = LimitDirection(direction_raw)
    except (ValueError, TypeError):
        direction = LimitDirection.HIGH

    return ParameterLimit(
        param_name=str(data.get("param_name") or param_name),
        display_name=str(
            data.get("display_name")
            or data.get("param_name")
            or param_name
        ),
        unit=str(data.get("unit", "")),
        normal_min=float(data.get("normal_min", 0.0)),
        normal_max=float(data.get("normal_max", 0.0)),
        warning_pct=float(data.get("warning_pct", 0.10)),
        critical_pct=float(data.get("critical_pct", 0.25)),
        direction=direction,
        event_type_name=str(
            data.get("event_type_name", "custom")
        ),
    )


def _registry_from_defaults() -> LimitsRegistry:
    """Create an independent registry without sharing mutable defaults."""
    return LimitsRegistry(deepcopy(DEFAULT_LIMITS))


def save_profile(
    name: str,
    registry: LimitsRegistry,
    description: str = "",
) -> Path:
    """Save or overwrite a limits profile as JSON."""
    if not isinstance(registry, LimitsRegistry):
        raise TypeError("registry must be a LimitsRegistry")

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    path = _profile_path(name)

    payload = {
        "schema_version": 1,
        "name": str(name).strip(),
        "description": str(description),
        "created_or_updated_at": datetime.now(UTC).isoformat(),
        "limits": {
            key: _limit_to_storage(limit)
            for key, limit in registry._limits.items()
        },
    }

    temporary_path = path.with_suffix(".json.tmp")

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(path)
    return path


def load_profile(name: str) -> Optional[LimitsRegistry]:
    """Load a profile, returning None when it does not exist."""
    path = _profile_path(name)

    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    limits_data = payload.get("limits", {})

    if not isinstance(limits_data, dict):
        return None

    registry = LimitsRegistry({})
    registry._limits = {}

    for param_name, data in limits_data.items():
        if not isinstance(data, dict):
            continue

        limit = _limit_from_storage(param_name, data)
        registry.set(limit)

    return registry


def list_profiles() -> List[Dict[str, Any]]:
    """Return profile metadata for the API and Limits Editor."""
    ensure_default_profiles()

    profiles: List[Dict[str, Any]] = []

    for path in sorted(
        PROFILE_DIR.glob("*.json"),
        key=lambda p: p.name.lower(),
    ):
        try:
            payload = json.loads(
                path.read_text(encoding="utf-8")
            )

            limits_data = payload.get("limits", {})

            profiles.append({
                "name": payload.get("name", path.stem),
                "description": payload.get("description", ""),
                "updated_at": payload.get(
                    "created_or_updated_at", ""
                ),
                "n_limits": (
                    len(limits_data)
                    if isinstance(limits_data, dict)
                    else 0
                ),
                "filename": path.name,
                "is_default": (
                    payload.get("name") == DEFAULT_PROFILE_NAME
                ),
            })

        except (
            OSError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            profiles.append({
                "name": path.stem,
                "description": "Unreadable profile",
                "updated_at": "",
                "n_limits": 0,
                "filename": path.name,
                "is_default": False,
                "error": "invalid_profile_file",
            })

    return profiles


def delete_profile(name: str) -> bool:
    """Delete a user profile. The Default profile is protected."""
    if str(name).strip().lower() == DEFAULT_PROFILE_NAME.lower():
        return False

    path = _profile_path(name)

    if not path.exists():
        return False

    path.unlink()
    return True


def ensure_default_profiles() -> Path:
    """Create the Default profile when it does not exist."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    default_path = _profile_path(DEFAULT_PROFILE_NAME)

    if not default_path.exists():
        save_profile(
            DEFAULT_PROFILE_NAME,
            _registry_from_defaults(),
            "ARHPP built-in mechanical operating limits",
        )

    return default_path
