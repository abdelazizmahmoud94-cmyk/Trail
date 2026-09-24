"""Maintenance & Sensor Troubleshoot Report."""

from datetime import datetime
from typing import Dict, List, Optional


class MaintenanceReport:
    report_type = "maintenance"

    def build(self, entries: List[Dict],
                sensors_status: Optional[Dict] = None) -> Dict:
        sections = []
        if sensors_status:
            rows = []
            for sensor, status in sensors_status.items():
                rows.append([sensor, status.get("status", "OK"),
                              status.get("last_calibration", "-"),
                              status.get("notes", "")])
            sections.append({
                "title": "Sensor Status", "type": "table",
                "content": {
                    "headers": ["Sensor", "Status", "Last Calibration", "Notes"],
                    "rows": rows}})
        rows = []
        for e in entries:
            rows.append([e.get("time", ""), e.get("equipment", ""),
                          e.get("issue", ""), e.get("action", ""),
                          e.get("technician", "")])
        sections.append({
            "title": "Maintenance Log", "type": "table",
            "content": {
                "headers": ["Time", "Equipment", "Issue", "Action", "Technician"],
                "rows": rows or [["-", "No entries", "-", "-", "-"]]}})
        return {"report_type": self.report_type, "sections": sections,
                 "generated_at": datetime.utcnow().isoformat()}
