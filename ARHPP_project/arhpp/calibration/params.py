"""Parameter registry — the tunable knobs of ARHPP."""

from dataclasses import dataclass, asdict
from typing import List, Dict


@dataclass
class TunableParam:
    name: str
    default: float
    lo: float
    hi: float
    unit: str = ""
    description: str = ""
    category: str = "general"

    def clamp(self, v: float) -> float:
        return max(self.lo, min(self.hi, float(v)))


REGISTRY: List[TunableParam] = [
    # Rheology temperature correction
    TunableParam("k_temp_factor", 0.97, 0.80, 1.05, "",
                  "K at downhole T = K_ref * factor", "rheology"),
    TunableParam("tau_y_temp_factor", 0.98, 0.80, 1.05, "",
                  "tau_y at downhole T", "rheology"),

    # Eccentricity correction (Haciislamoglu)
    TunableParam("ecc_a", 0.072, 0.03, 0.15, "", "Haciislamoglu a", "annular"),
    TunableParam("ecc_b", 1.500, 1.00, 2.00, "", "Haciislamoglu b", "annular"),
    TunableParam("ecc_c", 0.960, 0.60, 1.20, "", "Haciislamoglu c", "annular"),

    # RPM correction
    TunableParam("rpm_coeff", 0.10, 0.02, 0.25, "",
                  "RPM friction enhancement coefficient", "annular"),

    # Losses model
    TunableParam("loss_fric_share", 0.40, 0.10, 0.70, "",
                  "Fraction of loss from friction", "losses"),
    TunableParam("loss_hydro_share", 0.60, 0.30, 0.90, "",
                  "Fraction from hydrostatic column", "losses"),

    # Pore pressure hybrid weights
    TunableParam("w_dc", 0.40, 0.10, 0.70, "", "Weight of d-exponent", "pp"),
    TunableParam("w_sigma", 0.20, 0.05, 0.50, "", "Weight of sigma", "pp"),
    TunableParam("w_gas", 0.15, 0.05, 0.40, "", "Weight of gas", "pp"),
    TunableParam("w_temp", 0.10, 0.00, 0.30, "", "Weight of temperature", "pp"),
    TunableParam("w_field", 0.15, 0.00, 0.40, "", "Weight of field", "pp"),

    # Eaton exponents
    TunableParam("eaton_exp_dc", 1.20, 0.60, 2.00, "", "Eaton exp dc", "pp"),
    TunableParam("eaton_exp_sigma", 1.00, 0.60, 2.00, "", "Eaton exp sigma", "pp"),

    # Gas influence factor bands
    TunableParam("gif_low_ppg", 0.05, 0.00, 0.15, "ppg", "GIF low", "gas"),
    TunableParam("gif_mod_ppg", 0.15, 0.05, 0.30, "ppg", "GIF mod", "gas"),
    TunableParam("gif_high_ppg", 0.35, 0.15, 0.60, "ppg", "GIF high", "gas"),

    # Loss classification thresholds
    TunableParam("loss_seepage_max", 0.02, 0.005, 0.05, "", "Seepage", "losses"),
    TunableParam("loss_partial_max", 0.10, 0.05, 0.20, "", "Partial", "losses"),
    TunableParam("loss_severe_max", 0.50, 0.30, 0.70, "", "Severe", "losses"),

    # Gas thresholds
    TunableParam("gas_bg_baseline_max", 20.0, 5.0, 50.0, "", "BG baseline", "gas"),
    TunableParam("gas_cg_significant", 50.0, 20.0, 120.0, "", "CG threshold", "gas"),
    TunableParam("gas_tg_significant", 80.0, 40.0, 200.0, "", "TG threshold", "gas"),
    TunableParam("gas_pog_significant", 30.0, 10.0, 80.0, "", "POG threshold", "gas"),
    TunableParam("gas_solubility_obm", 0.35, 0.10, 0.60, "", "OBM solubility", "gas"),
    TunableParam("gas_sg_default", 0.65, 0.55, 1.20, "", "Gas SG default", "gas"),

    # GIF thresholds
    TunableParam("gif_low_gas_threshold", 30.0, 10.0, 60.0, "", "GIF low gas", "gas"),
    TunableParam("gif_mod_gas_threshold", 150.0, 80.0, 250.0, "", "GIF mod gas", "gas"),

    # PP overburden
    TunableParam("obg_shallow", 14.0, 12.0, 16.0, "ppg", "OBG shallow", "pp"),
    TunableParam("obg_deep", 18.0, 16.0, 22.0, "ppg", "OBG deep", "pp"),
    TunableParam("transition_tvd", 8000.0, 3000.0, 12000.0, "ft", "OBG transition", "pp"),
    TunableParam("mw_normal_ppg", 8.65, 8.33, 9.0, "ppg", "MW normal", "pp"),
    TunableParam("t_surface_f", 90.0, 60.0, 120.0, "F", "Surface temp", "pp"),
    TunableParam("gradient_normal_f_per_ft", 0.015, 0.008, 0.025, "F/ft", "Geothermal gradient", "pp"),
    TunableParam("inclination_pp_coeff", 0.002, 0.0, 0.005, "", "Inclination PP coeff", "pp"),

    # Mud physics
    TunableParam("mw_compressibility", 3.0e-6, 1.0e-6, 8.0e-6, "1/psi",
                  "MW compressibility", "rheology"),
    TunableParam("mw_thermal_expansion", 2.5e-4, 1.0e-4, 5.0e-4, "1/F",
                  "MW thermal expansion", "rheology"),

    # Kick detection weights
    TunableParam("kick_w_flow", 0.40, 0.10, 0.70, "", "Kick weight flow", "events"),
    TunableParam("kick_w_pit", 0.35, 0.10, 0.70, "", "Kick weight pit", "events"),
    TunableParam("kick_w_gas", 0.25, 0.05, 0.50, "", "Kick weight gas", "events"),
    TunableParam("kick_flow_threshold_gpm", 15.0, 5.0, 50.0, "gpm", "Flow threshold", "events"),
    TunableParam("kick_pit_threshold_bbl", 5.0, 1.0, 20.0, "bbl", "Pit threshold", "events"),
    TunableParam("kick_gas_threshold_units", 20.0, 5.0, 100.0, "units", "Gas threshold", "events"),
]


REGISTRY_BY_NAME: Dict[str, TunableParam] = {p.name: p for p in REGISTRY}


def default_values() -> Dict[str, float]:
    return {p.name: p.default for p in REGISTRY}


def clamp_values(values: Dict[str, float]) -> Dict[str, float]:
    out = {}
    for p in REGISTRY:
        if p.name in values:
            out[p.name] = p.clamp(values[p.name])
        else:
            out[p.name] = p.default
    return out


def normalize_pp_weights(values: Dict[str, float]) -> Dict[str, float]:
    keys = ["w_dc", "w_sigma", "w_gas", "w_temp", "w_field"]
    total = sum(values.get(k, 0.0) for k in keys)
    if total <= 0:
        return values
    for k in keys:
        values[k] = values.get(k, 0.0) / total
    return values


def registry_table() -> List[dict]:
    return [asdict(p) for p in REGISTRY]


def get_params_by_category(category: str) -> List[TunableParam]:
    return [p for p in REGISTRY if p.category == category]
