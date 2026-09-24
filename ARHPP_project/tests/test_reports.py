"""Reports tests."""

import tempfile
from pathlib import Path

from arhpp.reports.daily import DailyReport
from arhpp.reports.influx import InfluxReport
from arhpp.reports.operations import OperationsReport
from arhpp.reports.maintenance import MaintenanceReport
from arhpp.reports.exporter import ReportExporter


def test_daily_report():
    r = DailyReport()
    data = r.build(
        well_data={"well_name": "KU-1", "rig_name": "RIG-A"},
        drilling_data={"bit_md_start": 10000, "bit_md_end": 12000,
                        "rop_avg": 45, "rpm_avg": 120},
        hydraulics_data={"q_avg": 650, "spp_avg": 3200,
                           "bhp_avg": 9500, "ecd_avg": 13.5},
        events_data={"events": []})
    assert data["report_type"] == "daily"
    assert len(data["sections"]) >= 6


def test_influx_report():
    r = InfluxReport()
    data = r.build(
        kick_data={"severity": "moderate", "probability": 0.75,
                    "influx_bbl": 15.5},
        pit_data={"total_gain_bbl": 15.5},
        gas_data={"bg": 25, "cg": 80})
    assert data["report_type"] == "influx"


def test_operations_report():
    r = OperationsReport()
    data = r.build(timeline=[
        {"time": "06:00", "state": "Drilling",
         "description": "Started"}])
    assert data["report_type"] == "operations"


def test_exporter_json():
    with tempfile.TemporaryDirectory() as tmp:
        exp = ReportExporter(tmp)
        report = {"report_type": "test", "sections": [],
                    "generated_at": "2024-01-01"}
        p = exp.export_json(report, "test")
        assert p.exists()


def test_exporter_all():
    with tempfile.TemporaryDirectory() as tmp:
        exp = ReportExporter(tmp)
        report = {"report_type": "test", "sections": []}
        outputs = exp.export_all(report, "test")
        assert "json" in outputs
        assert "csv" in outputs
        assert "html" in outputs
