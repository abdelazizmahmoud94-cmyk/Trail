"""Base Report class."""

from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from pathlib import Path
import json


class ReportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    PDF = "pdf"


@dataclass
class ReportMetadata:
    report_id: str = ""
    title: str = ""
    well_name: str = ""
    rig_name: str = ""
    operator: str = ""
    field: str = ""
    report_type: str = ""
    date_start: str = ""
    date_end: str = ""
    created_at: str = dataclass_field(
        default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = "ARHPP"
    version: str = "2.0"


class BaseReport:
    report_type: str = "base"

    def __init__(self, metadata: Optional[ReportMetadata] = None):
        self.metadata = metadata or ReportMetadata()
        self.sections: List[Dict[str, Any]] = []

    def add_section(self, title: str, content: Any,
                     content_type: str = "text") -> None:
        self.sections.append({
            "title": title, "type": content_type, "content": content})

    def to_dict(self) -> dict:
        return {"metadata": self.metadata.__dict__,
                 "sections": self.sections}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_csv(self) -> str:
        lines = []
        lines.append(f"Report,{self.report_type}")
        lines.append(f"Well,{self.metadata.well_name}")
        lines.append(f"Date,{self.metadata.created_at}")
        lines.append("")
        for s in self.sections:
            lines.append(f"# {s['title']}")
            if s["type"] == "table":
                headers = s["content"].get("headers", [])
                rows = s["content"].get("rows", [])
                lines.append(",".join(str(h) for h in headers))
                for r in rows:
                    lines.append(",".join(str(v) for v in r))
            elif s["type"] == "text":
                lines.append(str(s["content"]))
            lines.append("")
        return "\n".join(lines)

    def save(self, path: Path,
              fmt: ReportFormat = ReportFormat.JSON) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == ReportFormat.JSON:
            path.write_text(self.to_json(), encoding="utf-8")
        elif fmt == ReportFormat.CSV:
            path.write_text(self.to_csv(), encoding="utf-8")
        return path
