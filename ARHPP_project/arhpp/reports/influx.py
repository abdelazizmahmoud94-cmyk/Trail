"""Influx / Kick Report."""

from datetime import datetime
from typing import Dict, List, Optional


class InfluxReport:
    report_type = "influx"

    def build(self, kick_data: Dict, pit_data: Dict, gas_data: Dict,
                actions_taken: Optional[List[str]] = None) -> Dict:
        sections = []
        sections.append({
            "title": "Kick Summary", "type": "table",
            "content": {
                "headers": ["Parameter", "Value", "Unit"],
                "rows": [
                    ["Detection Time", kick_data.get("detected_at", "-"), ""],
                    ["Kick Probability", kick_data.get("probability", 0), "%"],
                    ["Kick Severity", kick_data.get("severity", "-"), ""],
                    ["Influx Type", kick_data.get("influx_type", "-"), ""],
                    ["Influx Volume", kick_data.get("influx_bbl", 0), "bbl"],
                    ["Kick Rate", kick_data.get("kick_rate_gpm", 0), "gpm"],
                ]}})
        sections.append({
            "title": "Pit Data", "type": "table",
            "content": {
                "headers": ["Parameter", "Value", "Unit"],
                "rows": [
                    ["Pit Gain Total", pit_data.get("total_gain_bbl", 0), "bbl"],
                    ["Gain Rate", pit_data.get("gain_rate_bbl_hr", 0), "bbl/hr"],
                    ["Pit Volume Start", pit_data.get("pit_start", 0), "bbl"],
                    ["Pit Volume End", pit_data.get("pit_end", 0), "bbl"],
                ]}})
        sections.append({
            "title": "Gas Readings", "type": "table",
            "content": {
                "headers": ["Parameter", "Value", "Unit"],
                "rows": [
                    ["Background Gas", gas_data.get("bg", 0), "units"],
                    ["Connection Gas", gas_data.get("cg", 0), "units"],
                    ["Trip Gas", gas_data.get("tg", 0), "units"],
                    ["Pump-Off Gas", gas_data.get("pog", 0), "units"],
                    ["Max Total Gas", gas_data.get("total_max", 0), "units"],
                ]}})
        sections.append({
            "title": "Shut-In Pressures", "type": "table",
            "content": {
                "headers": ["Parameter", "Value", "Unit"],
                "rows": [
                    ["SIDPP", kick_data.get("sidpp_psi", 0), "psi"],
                    ["SICP", kick_data.get("sicp_psi", 0), "psi"],
                    ["SITP", kick_data.get("sitp_psi", 0), "psi"],
                    ["MAASP", kick_data.get("maasp_psi", 0), "psi"],
                ]}})
        if actions_taken:
            sections.append({
                "title": "Actions Taken", "type": "table",
                "content": {
                    "headers": ["#", "Action"],
                    "rows": [[i + 1, a]
                              for i, a in enumerate(actions_taken)]}})
        return {"report_type": self.report_type, "sections": sections,
                 "generated_at": datetime.utcnow().isoformat()}
