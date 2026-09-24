"""Calibration framework tests."""

from pathlib import Path
import tempfile

from arhpp.calibration.params import (
    default_values, clamp_values, normalize_pp_weights, REGISTRY,
)
from arhpp.calibration.persist import save, load
from arhpp.calibration.historical_loader import HistoricalWell
from arhpp.calibration.targets import compute_well_target


def test_default_values_cover_registry():
    d = default_values()
    assert len(d) == len(REGISTRY)
    for p in REGISTRY:
        assert p.name in d


def test_clamp_respects_bounds():
    v = {"k_temp_factor": 5.0, "ecc_a": -1.0}
    c = clamp_values(v)
    assert c["k_temp_factor"] <= 1.05
    assert c["ecc_a"] >= 0.03


def test_pp_weights_normalized():
    v = normalize_pp_weights({
        "w_dc": 2.0, "w_sigma": 2.0, "w_gas": 1.0,
        "w_temp": 1.0, "w_field": 1.0,
    })
    total = sum(v[k] for k in ["w_dc", "w_sigma", "w_gas",
                                 "w_temp", "w_field"])
    assert abs(total - 1.0) < 1e-6


def test_persist_roundtrip_deprecated():
    """persist.load always returns defaults."""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "cal.json"
        vals = default_values()
        vals["k_temp_factor"] = 0.93
        save(vals, p)
        loaded = load(p)
        assert abs(loaded["k_temp_factor"] - 0.97) < 1e-6


def test_profile_library_roundtrip():
    from arhpp.calibration.library import ProfileLibrary
    from arhpp.calibration.profile import CalibrationProfile

    with tempfile.TemporaryDirectory() as tmp:
        lib = ProfileLibrary(Path(tmp))
        profile = CalibrationProfile(
            name="Test Profile", values=default_values())
        profile.values["k_temp_factor"] = 0.93
        saved_path = lib.save(profile)
        assert saved_path.exists()
        lib2 = ProfileLibrary(Path(tmp))
        loaded = lib2.get(profile.id)
        assert loaded is not None
        assert abs(loaded.values["k_temp_factor"] - 0.93) < 1e-6


def test_target_composite_zero_on_perfect():
    well = HistoricalWell(
        well_id="W1", md_ft=10000, tvd_ft=10000,
        mw_in_ppg=10.0, mw_out_ppg=10.0,
        pwd_bhp_psi=5200, pwd_ecd_ppg=10.0,
        spp_measured_psi=2000, pp_reference_ppg=9.0)
    t = compute_well_target(
        well=well, pred_bhp=5200, pred_ecd=10.0,
        pred_spp=2000, pred_pp=9.0,
        pred_kick_severity="none", pred_loss_class="none")
    assert t.composite < 1e-6
