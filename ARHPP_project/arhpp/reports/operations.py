"""Operations Log Report."""

from datetime import datetime
from typing import Dict, List, Optional


class OperationsReport:
    report_type = "operations"

    def build(self, timeline: List[Dict],
                shift_summary: Optional[Dict] = None) -> Dict:
        sections = []
        if shift_summary:
            sections.append({
                "title": "Shift Summary", "type": "table",
                "content": {
                    "headers": ["Parameter", "Value"],
                    "rows": [
                        ["Driller", shift_summary.get("driller", "-")],
                        ["Toolpusher", shift_summary.get("toolpusher", "-")],
                        ["Company Man", shift_summary.get("company_man", "-")],
                        ["Shift Start", shift_summary.get("shift_start", "-")],
                        ["Shift End", shift_summary.get("shift_end", "-")],
                    ]}})
        rows = []
        for i, ev in enumerate(timeline):
            rows.append([i + 1, ev.get("time", ""), ev.get("state", ""),
                          ev.get("description", ""), ev.get("depth_ft", ""),
                          ev.get("duration_min", "")])
        sections.append({
            "title": "Operations Timeline", "type": "table",
            "content": {
                "headers": ["#", "Time", "Rig State", "Description",
                              "Depth (ft)", "Duration (min)"],
                "rows": rows}})
        return {"report_type": self.report_type, "sections": sections,
                 "generated_at": datetime.utcnow().isoformat()}
