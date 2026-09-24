"""Save / load ML models."""

import pickle
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


def _path(name: str) -> Path:
    return MODELS_DIR / f"{name}.pkl"


def save_model(model, name: str) -> Path:
    p = _path(name)
    with open(p, "wb") as f:
        pickle.dump(model, f)
    return p


def load_model(name: str):
    p = _path(name)
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return pickle.load(f)


def has_model(name: str) -> bool:
    return _path(name).exists()
