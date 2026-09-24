"""Calibration Profile — named parameter set."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Optional
import uuid
import json

from arhpp.calibration.params import default_values, clamp_values


@dataclass
class CalibrationProfile:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Untitled Profile"
    description: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat())
    values: Dict[str, float] = field(default_factory=default_values)
    metadata: Dict = field(default_factory=dict)
    is_builtin: bool = False

    def get(self, param_name: str,
              default: Optional[float] = None) -> float:
        if param_name in self.values:
            return self.values[param_name]
        if default is not None:
            return default
        from arhpp.calibration.params import REGISTRY_BY_NAME
        spec = REGISTRY_BY_NAME.get(param_name)
        return spec.default if spec else 0.0

    def update_values(self, new_values: Dict[str, float]) -> "CalibrationProfile":
        merged = dict(self.values)
        merged.update(new_values)
        merged = clamp_values(merged)
        return CalibrationProfile(
            id=self.id, name=self.name, description=self.description,
            created_at=self.created_at, values=merged,
            metadata=dict(self.metadata), is_builtin=self.is_builtin)

    def clone_with_name(self, new_name: str) -> "CalibrationProfile":
        return CalibrationProfile(
            name=new_name,
            description=f"Clone of {self.name}",
            values=dict(self.values),
            metadata=dict(self.metadata))

    def diff_from_default(self) -> Dict[str, tuple]:
        defaults = default_values()
        out = {}
        for name, val in self.values.items():
            dflt = defaults.get(name, val)
            if abs(val - dflt) > 1e-6:
                out[name] = (dflt, val, val - dflt)
        return out

    def summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "n_params": len(self.values),
            "n_changed": len(self.diff_from_default()),
            "is_builtin": self.is_builtin,
            "metadata": self.metadata,
        }

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "values": dict(self.values),
            "metadata": dict(self.metadata),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationProfile":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            created_at=data.get("created_at",
                                  datetime.utcnow().isoformat()),
            values=clamp_values(data.get("values", default_values())),
            metadata=data.get("metadata", {}))

    @classmethod
    def from_json(cls, text: str) -> "CalibrationProfile":
        return cls.from_dict(json.loads(text))


def default_profile() -> CalibrationProfile:
    return CalibrationProfile(
        name="Default (System)",
        description="System defaults — no calibration applied",
        metadata={"source": "system_defaults"},
        is_builtin=True)
