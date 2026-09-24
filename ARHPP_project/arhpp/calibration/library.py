"""Profile Library — manage saved calibration profiles."""

import json
from pathlib import Path
from typing import List, Optional, Dict

from arhpp.calibration.profile import (
    CalibrationProfile, default_profile,
)


class ProfileLibrary:
    def __init__(self, root: Optional[Path] = None):
        if root is None:
            root = (Path(__file__).resolve().parent.parent.parent
                    / "calibration_profiles")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, CalibrationProfile] = {}
        self._refresh_cache()

    def list_profiles(self) -> List[dict]:
        self._refresh_cache()
        return [p.summary() for p in self._cache.values()]

    def get(self, profile_id: str) -> Optional[CalibrationProfile]:
        return self._cache.get(profile_id)

    def get_by_name(self, name: str) -> Optional[CalibrationProfile]:
        for p in self._cache.values():
            if p.name == name:
                return p
        return None

    def save(self, profile: CalibrationProfile,
              overwrite: bool = False) -> Path:
        existing = self._cache.get(profile.id)
        if existing and not overwrite:
            raise FileExistsError(
                f"Profile {profile.id} already exists. Use overwrite=True.")
        path = self._path_for(profile)
        path.write_text(profile.to_json(), encoding="utf-8")
        self._cache[profile.id] = profile
        return path

    def delete(self, profile_id: str) -> bool:
        p = self._cache.get(profile_id)
        if not p:
            return False
        path = self._path_for(p)
        if path.exists():
            path.unlink()
        del self._cache[profile_id]
        return True

    def duplicate(self, profile_id: str,
                    new_name: str) -> Optional[CalibrationProfile]:
        src = self._cache.get(profile_id)
        if not src:
            return None
        new = src.clone_with_name(new_name)
        self.save(new)
        return new

    def import_from_file(self, path: Path) -> CalibrationProfile:
        text = Path(path).read_text(encoding="utf-8")
        profile = CalibrationProfile.from_json(text)
        self.save(profile)
        return profile

    def export_to_file(self, profile_id: str, path: Path) -> bool:
        p = self._cache.get(profile_id)
        if not p:
            return False
        Path(path).write_text(p.to_json(), encoding="utf-8")
        return True

    def get_default(self) -> CalibrationProfile:
        return default_profile()

    def _path_for(self, profile: CalibrationProfile) -> Path:
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in profile.name)[:40]
        return self.root / f"{safe_name}_{profile.id}.json"

    def _refresh_cache(self) -> None:
        self._cache.clear()
        if not self.root.exists():
            return
        for f in sorted(self.root.glob("*.json")):
            try:
                text = f.read_text(encoding="utf-8")
                profile = CalibrationProfile.from_json(text)
                self._cache[profile.id] = profile
            except Exception:
                continue


_library: Optional[ProfileLibrary] = None


def get_library() -> ProfileLibrary:
    global _library
    if _library is None:
        _library = ProfileLibrary()
    return _library
