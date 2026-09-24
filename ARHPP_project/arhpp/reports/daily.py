"""Daily Drilling Report."""

from datetime import datetime
from typing import Dict, List, Optional


class DailyReport:
    report_type = "daily"

    def __init__(self):
        self.metadata = None
        self.sections = []

    def build(self, well_data: Dict, drilling_data: Dict,
                hydraulics_data: Dict, events_data: Dict,
                operational_summary: str = "") -> Dict:
        self.sections.append({
            "title": "Job Information", "type": "table",
            "content": {
                "headers": ["Parameter", "Value"],
                "rows": [
                    ["Well", well_data.get("well_name", "-")],
                    ["Rig", well_data.get("rig_name", "-")],
                    ["Operator", well_data.get("operator", "-")],
                    ["Field", well_data.get("field", "-")],
                    ["Report Date", datetime.utcnow().strftime("%Y-%m-%d")],
                    ["Report Time", datetime.utcnow().strftime("%H:%M:%S")],
                ]}})
        self.sections.append({
            "title": "Drilling Summary", "type": "table",
            "content": {
                "headers": ["Parameter", "Value", "Unit"],
                "rows": [
                    ["Bit Depth Start", drilling_data.get("bit_md_start", 0), "ft"],
                    ["Bit Depth End", drilling_data.get("bit_md_end", 0), "ft"],
                    ["Drilled Footage", (drilling_data.get("bit_md_end", 0)
                                          - drilling_data.get("bit_md_start", 0)), "ft"],
                    ["ROP (avg)", drilling_data.get("rop_avg", 0), "ft/hr"],
                    ["RPM (avg)", drilling_data.get("rpm_avg", 0), "rpm"],
                    ["WOB (avg)", drilling_data.get("wob_avg", 0), "klb"],
                    ["Torque (avg)", drilling_data.get("torque_avg", 0), "ft-lb"],
                    ["Rotating Hours", drilling_data.get("rotating_hours", 0), "hr"],
                    ["Circulating Hours", drilling_data.get("circulating_hours", 0), "hr"],
                ]}})
        self.sections.append({
            "title": "Hydraulics", "type": "table",
            "content": {
                "headers": ["Parameter", "Value", "Unit"],
                "rows": [
                    ["Flow Rate (avg)", hydraulics_data.get("q_avg", 0), "gpm"],
                    ["SPP (avg)", hydraulics_data.get("spp_avg", 0), "psi"],
                    ["SBP (avg)", hydraulics_data.get("sbp_avg", 0), "psi"],
                    ["BHP (avg)", hydraulics_data.get("bhp_avg", 0), "psi"],
                    ["ECD (avg)", hydraulics_data.get("ecd_avg", 0), "ppg"],
                    ["Bit dP (avg)", hydraulics_data.get("bit_dp_avg", 0), "psi"],
                ]}})
        self.sections.append({
            "title": "Mud Properties", "type": "table",
            "content": {
                "headers": ["Parameter", "Value", "Unit"],
                "rows": [
                    ["MW In", drilling_data.get("mw_in", 0), "ppg"],
                    ["MW Out", drilling_data.get("mw_out", 0), "ppg"],
                    ["Temperature In", drilling_data.get("temp_in", 0), "F"],
                    ["Temperature Out", drilling_data.get("temp_out", 0), "F"],
                    ["Pit Volume", drilling_data.get("pit_volume", 0), "bbl"],
                    ["Pit Gain", drilling_data.get("pit_gain", 0), "bbl"],
                ]}})
        events_rows = []
        for ev in events_data.get("events", []):
            events_rows.append([ev.get("time", ""), ev.get("type", ""),
                                  ev.get("severity", ""),
                                  ev.get("description", "")])
        if not events_rows:
            events_rows = [["-", "No events", "-", "-"]]
        self.sections.append({
            "title": "Events & Alarms", "type": "table",
            "content": {
                "headers": ["Time", "Type", "Severity", "Description"],
                "rows": events_rows}})
        self.sections.append({
            "title": "Operational Summary", "type": "text",
            "content": operational_summary or "Normal drilling operations."})
        return {"report_type": self.report_type, "sections": self.sections,
                 "generated_at": datetime.utcnow().isoformat()}
