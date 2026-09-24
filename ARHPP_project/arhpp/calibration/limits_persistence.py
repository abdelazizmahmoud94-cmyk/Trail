"""Persist and load mechanical limits — separate JSON profiles."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from arhpp.mechanics.limits_config import (
    ParameterLimit, LimitsRegistry, LimitDirection,
)


BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROFILES_DIR = BASE_DIR / "mechanics_limits"
PROFILES_DIR.mkdir(exist_ok=True)


def _path_for(name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return PROFILES_DIR / f"{safe}.json"


def save_profile(name: str, registry: LimitsRegistry,
                   description: str = "",
                   metadata: Optional[dict] = None) -> Path:
    p = _path_for(name)
    payload = {
        "name": name,
        "description": description,
        "saved_at": datetime.utcnow().isoformat(),
        "metadata": metadata or {},
        "limits": registry.to_dict(),
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def load_profile(name: str) -> Optional[LimitsRegistry]:
    p = _path_for(name)
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    reg = LimitsRegistry({})
    reg._limits = {}
    for pname, ldata in data.get("limits", {}).items():
        limit = ParameterLimit(
            param_name=ldata["param_name"],
            display_name=ldata["display_name"],
            unit=ldata["unit"],
            normal_min=ldata["normal_min"],
            normal_max=ldata["normal_max"],
            warning_pct=ldata["warning_pct"],
            critical_pct=ldata["critical_pct"],
            direction=LimitDirection(ldata["direction"]),
            event_type_name=ldata.get("event_type_name", "custom"),
        )
        reg.set(limit)
    return reg


def list_profiles() -> List[dict]:
    out = []
    for p in sorted(PROFILES_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append({
                "name": data.get("name", p.stem),
                "description": data.get("description", ""),
                "saved_at": data.get("saved_at", ""),
                "n_limits": len(data.get("limits", {})),
                "is_builtin": data.get("metadata", {}).get("builtin", False),
            })
        except Exception:
            continue
    return out


def delete_profile(name: str) -> bool:
    p = _path_for(name)
    if p.exists():
        p.unlink()
        return True
    return False


def ensure_default_profiles() -> None:
    if list(PROFILES_DIR.glob("*.json")):
        return

    reg = LimitsRegistry()
    save_profile(name="Default", registry=reg,
                  description="System defaults",
                  metadata={"builtin": True})

    reg2 = LimitsRegistry()
    reg2.update("hookload_klb", normal_max=650)
    reg2.update("surface_torque_ftlb", normal_max=28000)
    reg2.update("spp_psi", normal_max=6500)
    save_profile(name="Onshore Heavy", registry=reg2,
                  description="Heavy land rig",
                  metadata={"builtin": True})

    reg3 = LimitsRegistry()
    reg3.update("bhp_psi", normal_max=12000, warning_pct=0.03,
                 critical_pct=0.08)
    reg3.update("ecd_ppg", normal_max=14.0)
    reg3.update("sbp_psi", normal_max=1200)
    save_profile(name="Offshore MPD", registry=reg3,
                  description="MPD offshore tight margins",
                  metadata={"builtin": True})

    reg4 = LimitsRegistry()
    reg4.update("vibration_g", normal_max=2.0, warning_pct=0.25,
                 critical_pct=0.75)
    reg4.update("overpull_klb", normal_max=50, warning_pct=0.30,
                 critical_pct=0.80)
    save_profile(name="Exploration Risky", registry=reg4,
                  description="Exploratory well conservative",
                  metadata={"builtin": True})
