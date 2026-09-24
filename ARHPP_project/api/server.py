"""ARHPP API — FastAPI server with WebSocket + Dashboard endpoints."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.state import STATE

log = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
STATIC.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════
#  Background ingestion (demo)
# ═══════════════════════════════════════════════════════════════

_ingest_task: Optional[asyncio.Task] = None


async def _demo_ingest():
    """Fake ingestion loop for demo — generates plausible data."""
    import random
    while True:
        t = STATE.tick_count
        snap = {
            "timestamp": datetime.utcnow().isoformat(),
            "bit_md": 15000 + random.random() * 100,
            "q_in": 650 + random.uniform(-5, 5),
            "q_out": 650 + random.uniform(-8, 8),
            "spp": 3200 + random.uniform(-30, 30),
            "sbp": 250 + random.uniform(-5, 5),
            "bhp": 9500 + random.uniform(-50, 50),
            "ecd": 13.5 + random.uniform(-0.05, 0.05),
            "esd": 13.2 + random.uniform(-0.03, 0.03),
            "pp": 9.2 + random.uniform(-0.05, 0.05),
            "fg": 17.5,
            "mw": 13.5,
            "kick_probability": max(0.0, random.gauss(0.05, 0.02)),
            "confidence": 0.9 + random.uniform(-0.05, 0.05),
            "overall_risk": "NONE",
            "alerts": [],
            "q_utube": random.uniform(-2, 2),
            "q_loss": 0.0,
        }
        STATE.push(snap)
        await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ingest_task
    _ingest_task = asyncio.create_task(_demo_ingest())
    yield
    if _ingest_task:
        _ingest_task.cancel()


app = FastAPI(title="ARHPP API", version="2.0.0", lifespan=lifespan)

if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


# ═══════════════════════════════════════════════════════════════
#  Health & Info
# ═══════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {"status": "ok", "tick_count": STATE.tick_count}


@app.get("/api/version")
async def version():
    import sys
    from arhpp import __version__
    return {
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": sys.platform,
    }


@app.get("/api/metrics")
async def metrics():
    from arhpp.monitoring.metrics import get_metrics
    return get_metrics().snapshot()


@app.get("/api/health/full")
async def health_full():
    from arhpp.monitoring.health import default_health_checker
    hc = default_health_checker()
    return hc.run_all()


# ═══════════════════════════════════════════════════════════════
#  Live dashboard state
# ═══════════════════════════════════════════════════════════════

@app.get("/api/dashboard")
async def dashboard():
    return JSONResponse(STATE.snapshot())


@app.get("/api/latest")
async def latest():
    return STATE.latest or {}


@app.get("/api/history")
async def history(n: int = 300):
    return {"history": STATE.get_history(n)}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    last_tick = -1
    try:
        while True:
            if STATE.tick_count != last_tick:
                last_tick = STATE.tick_count
                snap = STATE.latest
                if snap:
                    await ws.send_json(snap)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
#  Visualization endpoints
# ═══════════════════════════════════════════════════════════════

from arhpp.viz.channel_manager import get_channel_manager
from arhpp.viz.graphs import GraphBuilder, GraphSpec
from arhpp.viz.trajectory import TrajectoryEngine
from arhpp.viz.wellbore import WellboreSchematic
from arhpp.viz.trip_tank import VirtualTripTank

_graph_builder = GraphBuilder()
_trajectory_engine = TrajectoryEngine()
_trip_tank = VirtualTripTank()


@app.get("/api/viz/channels")
async def viz_channels():
    cm = get_channel_manager()
    return {"channels": cm.to_dict_list(), "stats": cm.stats()}


@app.get("/api/viz/graphs/main")
async def viz_main_graphs(duration_s: float = 240.0,
                             units: str = "imperial"):
    specs = GraphBuilder.main_graph_specs()
    for spec in specs:
        spec.duration_s = duration_s
        spec.units = units
    graphs = [_graph_builder.build(spec) for spec in specs]
    return {"graphs": graphs}


@app.get("/api/viz/trajectory")
async def viz_trajectory():
    try:
        from excel_templates import reader as xl
        from arhpp.geometry.survey import compute_survey
        survey = compute_survey(xl.read_survey())
    except Exception:
        from arhpp.core.types import SurveyPoint
        from arhpp.geometry.survey import compute_survey
        survey = compute_survey([
            SurveyPoint(0, 0, 0),
            SurveyPoint(5000, 15, 90),
            SurveyPoint(10000, 30, 90),
            SurveyPoint(15690, 28, 95),
        ])
    package = _trajectory_engine.compute_full_package(survey)
    package["well_name"] = "KU-EXAMPLE-1"
    return package


@app.get("/api/viz/wellbore")
async def viz_wellbore():
    try:
        from excel_templates import reader as xl
        sections = xl.read_hole_program()
        schematic = WellboreSchematic.from_hole_sections(sections)
    except Exception:
        schematic = WellboreSchematic()
        schematic.add_casing("Surface", 0, 3000, 18.625, 17.76)
        schematic.add_casing("Intermediate", 0, 10000, 13.375, 12.415)
        schematic.add_casing("Production", 0, 14800, 9.625, 8.681)
        schematic.add_open_hole("Open Hole", 14800, 15690, 6.0)
    if not schematic.formations:
        schematic.kuwait_formations_preload()
    return schematic.to_dict()


# ═══════════════════════════════════════════════════════════════
#  Limits + Events (mechanical)
# ═══════════════════════════════════════════════════════════════

from arhpp.mechanics.limits_persistence import (
    ensure_default_profiles, list_profiles, load_profile,
    save_profile, delete_profile,
)
from arhpp.mechanics.limits_config import (
    get_limits_registry, LimitsRegistry, LimitDirection,
    ParameterLimit,
)
from arhpp.mechanics.events import (
    get_event_tracker, EventType, EventState, EventSeverity,
)

ensure_default_profiles()
_active_profile_name: str = "Default"
_live_values_cache: dict = {}


@app.get("/api/limits/profiles")
async def limits_profiles():
    return {"profiles": list_profiles()}


@app.get("/api/limits/active")
async def limits_active():
    return {
        "active_profile": _active_profile_name,
        "limits": get_limits_registry().to_dict(),
    }


@app.post("/api/limits/activate")
async def limits_activate(payload: dict):
    global _active_profile_name
    name = payload.get("name")
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    reg = load_profile(name)
    if reg is None:
        return JSONResponse({"error": "profile not found"}, status_code=404)
    global_registry = get_limits_registry()
    global_registry._limits = reg._limits
    _active_profile_name = name
    return {"activated": name, "n_limits": len(reg._limits)}


@app.post("/api/limits/save")
async def limits_save(payload: dict):
    name = payload.get("name")
    description = payload.get("description", "")
    limits_dict = payload.get("limits")
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    reg = LimitsRegistry({})
    reg._limits = {}
    for pname, ldata in (limits_dict or {}).items():
        reg.set(ParameterLimit(
            param_name=ldata["param_name"],
            display_name=ldata["display_name"],
            unit=ldata["unit"],
            normal_min=ldata.get("normal_min", 0.0),
            normal_max=ldata.get("normal_max", 0.0),
            warning_pct=ldata.get("warning_pct", 0.10),
            critical_pct=ldata.get("critical_pct", 0.25),
            direction=LimitDirection(ldata.get("direction", "high")),
            event_type_name=ldata.get("event_type_name", "custom"),
        ))
    path = save_profile(name, reg, description)
    return {"saved": str(path), "name": name}


@app.delete("/api/limits/profiles/{name}")
async def limits_delete_profile(name: str):
    ok = delete_profile(name)
    return {"deleted": ok}


@app.post("/api/limits/reset_defaults")
async def limits_reset_defaults():
    global _active_profile_name
    reg = get_limits_registry()
    reg.reset_to_defaults()
    _active_profile_name = "Default"
    return {"reset": True, "active_profile": "Default"}


@app.get("/api/limits/live_values")
async def limits_live_values():
    return {"values": dict(_live_values_cache)}


@app.post("/api/limits/feed_batch")
async def limits_feed_batch(payload: dict):
    tracker = get_event_tracker()
    values = payload.get("values", {})
    md_ft = float(payload.get("md_ft", 0))
    tvd_ft = float(payload.get("tvd_ft", 0))
    operation = payload.get("operation", "")
    touched = tracker.update_snapshot(
        values=values, md_ft=md_ft, tvd_ft=tvd_ft, operation=operation)
    _live_values_cache.update(values)
    return {
        "touched_count": len(touched),
        "events": [e.to_dict() for e in touched],
        "stats": tracker.get_stats(),
    }


@app.get("/api/events")
async def events_list(state: Optional[str] = None,
                       type_: Optional[str] = None,
                       md_min: Optional[float] = None,
                       md_max: Optional[float] = None,
                       include_terminal: bool = True):
    tracker = get_event_tracker()
    state_filter = None
    if state:
        try:
            state_filter = [EventState(s.strip())
                              for s in state.split(",")]
        except ValueError:
            pass
    type_filter = None
    if type_:
        try:
            type_filter = [EventType(t.strip())
                             for t in type_.split(",")]
        except ValueError:
            pass
    out = []
    for ev in tracker.get_all_events():
        if not include_terminal and ev.is_terminal():
            continue
        if state_filter and ev.state not in state_filter:
            continue
        if type_filter and ev.event_type not in type_filter:
            continue
        if md_min is not None and ev.md_ft < md_min:
            continue
        if md_max is not None and ev.md_ft > md_max:
            continue
        out.append(ev.to_dict())
    out.sort(key=lambda e: e["md_ft"])
    return {"events": out, "stats": tracker.get_stats()}


@app.get("/api/events/feedback")
async def events_feedback(limit: int = 200):
    tracker = get_event_tracker()
    return {"log": tracker.get_feedback_log(limit=limit),
             "stats": tracker.get_stats()}


@app.post("/api/events/{event_id}/clear")
async def events_clear(event_id: str, payload: dict = None):
    tracker = get_event_tracker()
    payload = payload or {}
    ok = tracker.clear_manually(
        event_id,
        operator=payload.get("operator", "operator"),
        note=payload.get("note", ""))
    if not ok:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"cleared": True}


@app.post("/api/events/{event_id}/false_positive")
async def events_false_positive(event_id: str, payload: dict = None):
    tracker = get_event_tracker()
    payload = payload or {}
    ok = tracker.mark_false_positive(
        event_id,
        operator=payload.get("operator", "operator"),
        note=payload.get("note", ""))
    if not ok:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"marked": True}


@app.post("/api/events/reset")
async def events_reset():
    tracker = get_event_tracker()
    tracker.reset()
    return {"reset": True}


@app.get("/api/events/schematic")
async def events_schematic():
    from arhpp.viz.wellbore import WellboreSchematic
    try:
        from excel_templates import reader as xl
        sections = xl.read_hole_program()
        schematic = WellboreSchematic.from_hole_sections(sections)
    except Exception:
        schematic = WellboreSchematic()
        schematic.add_casing("Surface", 0, 3000, 18.625, 17.76)
        schematic.add_casing("Intermediate", 0, 10000, 13.375, 12.415)
        schematic.add_casing("Production", 0, 14800, 9.625, 8.681)
        schematic.add_open_hole("Open Hole", 14800, 15690, 6.0)
    if not schematic.formations:
        schematic.kuwait_formations_preload()
    bit_md = 15690.0
    tracker = get_event_tracker()
    base = schematic.to_dict()
    base["bit_md_ft"] = bit_md
    base["events"] = [e.to_dict() for e in tracker.get_all_events()]
    base["events_stats"] = tracker.get_stats()
    base["limits"] = get_limits_registry().to_dict()
    return base


# ═══════════════════════════════════════════════════════════════
#  Calibration Sandbox
# ═══════════════════════════════════════════════════════════════

from arhpp.calibration.library import get_library
from arhpp.calibration.profile import (
    CalibrationProfile, default_profile,
)
from arhpp.calibration.sandbox import CalibrationSandbox
from arhpp.calibration.params import default_values
from arhpp.calibration.historical_loader import load_wells_from_excel

_sandbox: CalibrationSandbox = CalibrationSandbox()


@app.get("/api/calibration/profiles")
async def calibration_profiles():
    lib = get_library()
    profiles = [lib.get_default().summary()] + lib.list_profiles()
    return {"profiles": profiles}


@app.get("/api/calibration/profiles/{profile_id}")
async def calibration_profile_get(profile_id: str):
    lib = get_library()
    if profile_id == "default":
        return default_profile().to_dict()
    p = lib.get(profile_id)
    if not p:
        return JSONResponse({"error": "not found"}, status_code=404)
    return p.to_dict()


@app.post("/api/calibration/profiles")
async def calibration_profile_create(payload: dict):
    lib = get_library()
    profile = CalibrationProfile(
        name=payload.get("name", "New Profile"),
        description=payload.get("description", ""),
        values=payload.get("values", default_values()))
    lib.save(profile)
    return profile.to_dict()


@app.delete("/api/calibration/profiles/{profile_id}")
async def calibration_profile_delete(profile_id: str):
    lib = get_library()
    ok = lib.delete(profile_id)
    return {"deleted": ok}


@app.post("/api/calibration/profiles/{profile_id}/duplicate")
async def calibration_profile_duplicate(profile_id: str, payload: dict):
    lib = get_library()
    new = lib.duplicate(profile_id, payload.get("name", "Copy"))
    return new.to_dict() if new else {"error": "not found"}


@app.get("/api/calibration/params/defaults")
async def calibration_params_defaults():
    return {"values": default_values()}


@app.get("/api/calibration/wells")
async def calibration_wells():
    return {"wells": _sandbox.list_wells_summary()}


@app.post("/api/calibration/wells/load")
async def calibration_wells_load(payload: dict):
    path = Path(payload.get("path",
                              "excel_input/30_Historical_Wells.xlsx"))
    if not path.exists():
        return JSONResponse({"error": f"file not found: {path}"},
                              status_code=404)
    wells = load_wells_from_excel(path)
    _sandbox.load_wells(wells)
    return {"loaded": len(wells),
             "wells": _sandbox.list_wells_summary()}


@app.post("/api/calibration/run")
async def calibration_run(payload: dict):
    profile_id = payload.get("profile_id")
    lib = get_library()
    if profile_id == "default":
        profile = default_profile()
    else:
        profile = lib.get(profile_id)
        if not profile:
            return JSONResponse({"error": "profile not found"},
                                  status_code=404)
    if not _sandbox.wells:
        default_path = Path("excel_input/30_Historical_Wells.xlsx")
        if default_path.exists():
            _sandbox.load_wells(load_wells_from_excel(default_path))
    run = _sandbox.evaluate(profile)
    return {
        "run_id": run.run_id,
        "profile_id": profile.id,
        "profile_name": profile.name,
        "overall_score": run.overall_score,
        "duration_s": run.duration_s,
        "n_wells": len(run.wells),
        "well_targets": [
            {"well_id": t.well_id, "composite": t.composite,
             "e_bhp_psi": t.e_bhp_psi, "e_ecd_ppg": t.e_ecd_ppg,
             "e_spp_psi": t.e_spp_psi, "e_pp_ppg": t.e_pp_ppg}
            for t in run.well_targets],
    }


@app.get("/api/calibration/runs")
async def calibration_runs():
    return {"runs": [
        {"run_id": r.run_id, "profile_id": r.profile.id,
         "profile": {"name": r.profile.name, "id": r.profile.id},
         "overall_score": r.overall_score, "duration_s": r.duration_s,
         "n_wells": len(r.wells), "started_at": r.started_at,
         "wells": [w.well_id for w in r.wells],
         "well_targets": [
             {"well_id": t.well_id, "composite": t.composite,
              "e_bhp_psi": t.e_bhp_psi, "e_ecd_ppg": t.e_ecd_ppg}
             for t in r.well_targets]}
        for r in _sandbox.runs]}


@app.delete("/api/calibration/runs")
async def calibration_runs_clear():
    _sandbox.clear_runs()
    return {"cleared": True}


# ═══════════════════════════════════════════════════════════════
#  Reports
# ═══════════════════════════════════════════════════════════════

from arhpp.reports.daily import DailyReport
from arhpp.reports.influx import InfluxReport
from arhpp.reports.operations import OperationsReport
from arhpp.reports.maintenance import MaintenanceReport
from arhpp.reports.exporter import ReportExporter

_reports_exporter = ReportExporter("reports_output")
_latest_report: dict = {}


@app.post("/api/reports/daily")
async def report_daily():
    r = DailyReport()
    report = r.build(
        well_data={"well_name": "KU-EXAMPLE-1", "rig_name": "RIG-A",
                    "operator": "KOC", "field": "Field-A"},
        drilling_data={"bit_md_start": 15000, "bit_md_end": 15450,
                        "rop_avg": 45, "rpm_avg": 120, "wob_avg": 25,
                        "torque_avg": 18000, "rotating_hours": 8.5,
                        "circulating_hours": 12.0,
                        "mw_in": 13.5, "mw_out": 13.48,
                        "temp_in": 115, "temp_out": 180,
                        "pit_volume": 4200, "pit_gain": 0},
        hydraulics_data={"q_avg": 650, "spp_avg": 3200, "sbp_avg": 250,
                           "bhp_avg": 9500, "ecd_avg": 13.5,
                           "bit_dp_avg": 1250, "ann_fp_avg": 400},
        events_data={"events": []},
        operational_summary="Normal drilling operations.")
    _latest_report["daily"] = report
    return report


@app.post("/api/reports/influx")
async def report_influx():
    r = InfluxReport()
    report = r.build(
        kick_data={"detected_at": "2024-09-24 14:35",
                    "probability": 0.75, "severity": "moderate",
                    "influx_type": "gas", "influx_bbl": 15.5,
                    "kick_rate_gpm": 80, "sidpp_psi": 200,
                    "sicp_psi": 280, "sitp_psi": 150,
                    "maasp_psi": 800},
        pit_data={"total_gain_bbl": 15.5, "gain_rate_bbl_hr": 3.0,
                   "pit_start": 4200, "pit_end": 4215.5},
        gas_data={"bg": 25, "cg": 80, "tg": 0, "pog": 0,
                   "total_max": 120},
        actions_taken=[
            "Detected by auto kick detector (probability 75%)",
            "Choke A ramped to increase SBP to 450 psi",
            "Drilling stopped (RPM -> 0)",
            "Operator notified - kill procedure initiated"])
    _latest_report["influx"] = report
    return report


@app.post("/api/reports/operations")
async def report_operations():
    r = OperationsReport()
    report = r.build(
        timeline=[
            {"time": "06:00", "state": "Drilling",
             "description": "Resumed drilling", "depth_ft": 15000,
             "duration_min": 0},
            {"time": "07:30", "state": "Connection",
             "description": "Made connection", "depth_ft": 15090,
             "duration_min": 15},
            {"time": "09:45", "state": "Drilling",
             "description": "Resumed", "depth_ft": 15090,
             "duration_min": 0},
            {"time": "14:35", "state": "Kick",
             "description": "Kick detected", "depth_ft": 15450,
             "duration_min": 0}],
        shift_summary={"driller": "J. Smith",
                        "toolpusher": "M. Ali",
                        "company_man": "A. Khalid",
                        "shift_start": "06:00",
                        "shift_end": "18:00"})
    _latest_report["operations"] = report
    return report


@app.post("/api/reports/maintenance")
async def report_maintenance():
    r = MaintenanceReport()
    report = r.build(
        entries=[{"time": "08:00", "equipment": "SPP Sensor",
                   "issue": "Noisy signal",
                   "action": "Filter adjusted",
                   "technician": "Tech-A"}],
        sensors_status={
            "SPP": {"status": "OK", "last_calibration": "2024-08-01"},
            "SBP": {"status": "OK", "last_calibration": "2024-08-01"},
            "Flow Out": {"status": "WARNING",
                          "notes": "Intermittent",
                          "last_calibration": "2024-07-15"}})
    _latest_report["maintenance"] = report
    return report


@app.post("/api/reports/calibration")
async def report_calibration():
    from arhpp.calibration.params import REGISTRY
    rows = [[p.name, p.default, p.default, 0.0, p.category]
             for p in REGISTRY]
    return {
        "report_type": "calibration",
        "sections": [{
            "title": "Parameters", "type": "table",
            "content": {
                "headers": ["Param", "Default", "Current", "Delta",
                             "Category"],
                "rows": rows}}],
        "generated_at": datetime.utcnow().isoformat(),
    }


@app.post("/api/reports/export/{fmt}")
async def report_export(fmt: str):
    if not _latest_report:
        return JSONResponse({"error": "no report"}, status_code=400)
    report = list(_latest_report.values())[-1]
    base = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    if fmt == "json":
        p = _reports_exporter.export_json(report, base)
    elif fmt == "csv":
        p = _reports_exporter.export_csv(report, base)
    elif fmt == "html":
        p = _reports_exporter.export_html(report, base)
    elif fmt == "pdf":
        p = _reports_exporter.export_pdf(report, base)
    else:
        return JSONResponse({"error": "invalid format"}, status_code=400)
    return {"path": str(p), "format": fmt}


# ═══════════════════════════════════════════════════════════════
#  Page routing
# ═══════════════════════════════════════════════════════════════

def _page(name: str, fallback: str = None) -> HTMLResponse:
    idx = STATIC / name
    if idx.exists():
        return HTMLResponse(idx.read_text(encoding="utf-8"))
    return HTMLResponse(fallback or f"<h1>{name} missing</h1>")


@app.get("/", response_class=HTMLResponse)
async def root():
    return _page("dashboard.html")


@app.get("/calibration", response_class=HTMLResponse)
async def calibration_page():
    return _page("calibration.html")


@app.get("/trajectory", response_class=HTMLResponse)
async def trajectory_page():
    return _page("trajectory.html")


@app.get("/graphs", response_class=HTMLResponse)
async def graphs_page():
    return _page("graphs.html")


@app.get("/reports", response_class=HTMLResponse)
async def reports_page():
    return _page("reports.html")


@app.get("/well_live", response_class=HTMLResponse)
async def well_live_page():
    return _page("well_live.html")


@app.get("/mechanics", response_class=HTMLResponse)
async def mechanics_page():
    return _page("mechanics_dashboard.html")


def run():
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
