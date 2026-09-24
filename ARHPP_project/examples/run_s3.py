"""ARHPP S3 — Historical Calibration (Sandbox mode)."""

from pathlib import Path
import sys

from arhpp.calibration.historical_loader import load_wells_from_excel
from arhpp.calibration.optimizer import calibrate
from arhpp.calibration.library import get_library
from arhpp.calibration.profile import default_profile
from arhpp.calibration.sandbox import CalibrationSandbox
from arhpp.calibration.report import write_report
from arhpp.calibration.params import REGISTRY

BASE = Path(__file__).resolve().parent.parent
IN = BASE / "excel_input"


def main():
    print("=" * 70)
    print("  ARHPP S3 — Historical Calibration")
    print("  Mode: SANDBOX (isolated — Live System untouched)")
    print("=" * 70)

    xlsx = IN / "30_Historical_Wells.xlsx"
    if not xlsx.exists():
        print(f"Missing {xlsx}")
        print("Run: python -m excel_templates.build_templates")
        return 1

    wells = load_wells_from_excel(xlsx)
    print(f"\nLoaded {len(wells)} wells:")
    for w in wells:
        print(f"  {w.well_id:12s}  MD={w.md_ft:>7.0f}")

    if not wells:
        print("No wells loaded")
        return 1

    sandbox = CalibrationSandbox()
    sandbox.load_wells(wells)

    print("\nBASELINE (system defaults)")
    baseline = sandbox.evaluate(default_profile(), notes="baseline")
    print(f"  Score: {baseline.overall_score:.5f}")

    print(f"\nOPTIMIZING {len(REGISTRY)} parameters...")
    last_log = [0]

    def progress_cb(it, score, params):
        if it - last_log[0] >= 20:
            print(f"  [{it:>4}] score = {score:.5f}")
            last_log[0] = it

    result = calibrate(
        wells, base_profile=default_profile(),
        profile_name="S3 Auto-Calibrated",
        stages=(1, 2, 3, 4), refine=True,
        progress_cb=progress_cb)

    print("\nRESULTS")
    print(f"  Initial score : {result.initial_score:.5f}")
    print(f"  Final score   : {result.best_score:.5f}")
    print(f"  Improvement   : {result.improvement_pct:+.2f}%")
    print(f"  Params changed: {len(result.best_profile.diff_from_default())}")

    lib = get_library()
    saved_path = lib.save(result.best_profile)
    print(f"\nProfile saved: {saved_path.name}")

    out_xlsx = IN / "A9_Output_Calibration.xlsx"
    try:
        write_report(result, out_xlsx)
        print(f"Excel report: {out_xlsx}")
    except Exception as e:
        print(f"Excel report failed: {e}")

    # Verify Live System untouched
    from arhpp.calibration.context import is_live, get_param
    from arhpp.calibration.params import default_values
    assert is_live(), "Sandbox leaked!"
    ecc_a_live = get_param("ecc_a")
    ecc_a_default = default_values()["ecc_a"]
    assert abs(ecc_a_live - ecc_a_default) < 1e-9
    print("\nLive System untouched - defaults active")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
