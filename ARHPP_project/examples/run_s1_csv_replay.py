"""S1 - CSV Replay."""

import csv
from pathlib import Path

from arhpp.geometry.survey import compute_tvd
from arhpp.geometry.bha import stack_bha
from arhpp.hydraulics.bit import Nozzle
from arhpp.sensors.csv_replay import CSVReplayAdapter
from arhpp.sensors.realtime_loop import RealtimeLoop, RealtimeConfig
from excel_templates import reader as xl
from openpyxl import load_workbook


BASE = Path(__file__).resolve().parent.parent
IN = BASE / "excel_input"


def make_csv(p):
    if p.exists():
        return
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["MD_ft", "Bit_MD_ft", "ROP_ft_hr", "RPM",
                     "WOB_klb", "Torque_ftlb", "SPP_psi",
                     "Q_in_gpm", "Q_out_gpm", "Pit_Volume_bbl",
                     "SBP_psi", "Choke_pct", "MW_in_ppg",
                     "MW_out_ppg", "Temp_in_F", "Temp_out_F",
                     "TotalGas_units", "BG_units", "CG_units",
                     "TG_units", "POG_units", "PumpsOn",
                     "Connection", "TripMode"])
        for i in range(60):
            md = 10000 + i * 10
            w.writerow([md, md, 60 - i * 0.3, 120, 25, 18000,
                         3200 + i * 2, 650, 655, 4000 + i * 2,
                         250, 30, 13.5, 13.5, 90, 180 + i,
                         15, 12, 0, 0, 0, "TRUE", "FALSE",
                         "static"])


def main():
    print("ARHPP - S1 CSV Replay\n" + "=" * 60)
    survey = compute_tvd(xl.read_survey())
    sections = xl.read_hole_program()
    bha = stack_bha(xl.read_bha())
    raw_s = xl.read_fluid_segments_string()
    raw_a = xl.read_fluid_segments_annulus()
    bit_cfg = xl.read_bit_config()
    for r in raw_s + raw_a:
        r["tau_y"], r["k"], r["n"] = 10.0, 0.5, 0.7
    nozzles = [Nozzle(n["size_32nd_in"], n["tfa_in2"])
                for n in bit_cfg["nozzles"]]
    csv_p = IN / "23_realtime_stream.csv"
    make_csv(csv_p)
    adapter = CSVReplayAdapter(str(csv_p), dt_seconds=1.0)
    cfg = RealtimeConfig(survey=survey, hole_sections=sections,
                          bha=bha, bit_nozzles=nozzles,
                          bit_diameter_in=bit_cfg["bit_diameter_in"],
                          cd=bit_cfg["cd"],
                          string_segments_raw=raw_s,
                          annulus_segments_raw=raw_a,
                          tick_seconds=0.0)
    log = []

    def cb(out):
        reading = out["reading"]
        log.append({"time": reading.timestamp.isoformat(
            timespec="seconds"),
            "bit_md": reading.bit_md_ft,
            "q_in": reading.q_in_gpm,
            "q_out": reading.q_out_gpm,
            "spp": reading.spp_psi})
        if out["tick"] % 10 == 0:
            print(f"  t={out['tick']:>3} MD={reading.bit_md_ft:>7.0f} "
                  f"SPP={reading.spp_psi:.1f}")

    cfg.on_tick = cb
    loop = RealtimeLoop(adapter, cfg)
    loop.run(max_ticks=60)
    print(f"\n{len(log)} ticks processed")


