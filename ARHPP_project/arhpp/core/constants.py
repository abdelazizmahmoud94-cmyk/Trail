"""ARHPP — Physical and Petroleum Constants.

All conversions centralized here. No duplicates.
"""

# ═══════════════════════════════════════════════════════════════
#  PETROLEUM REFERENCE CONSTANTS
# ═══════════════════════════════════════════════════════════════

PSI_PER_FT_PER_PPG = 0.052
BBL_PER_FT_CONST = 1029.4
T_REF_F = 60.0
P_REF_PSI = 14.7
WATER_MW_PPG = 8.33
STEEL_DENSITY_PPG = 65.5


# ═══════════════════════════════════════════════════════════════
#  UNIT CONVERSION CONSTANTS (centralized — no duplicates)
# ═══════════════════════════════════════════════════════════════

# Length
INCH_TO_FT = 1.0 / 12.0
INCH_TO_M = 0.0254
FT_TO_M = 0.3048
M_TO_FT = 1.0 / 0.3048
MM_TO_IN = 1.0 / 25.4

# Volume
BBL_TO_GAL = 42.0
GAL_TO_BBL = 1.0 / 42.0
BBL_TO_M3 = 0.158987
M3_TO_BBL = 1.0 / 0.158987

# Flow
GPM_TO_M3S = 6.30902e-5
M3S_TO_GPM = 1.0 / 6.30902e-5
GPM_PER_BBL_MIN = 42.0

# Pressure
PA_TO_PSI = 1.450377e-4
PSI_TO_PA = 6894.757
KPA_TO_PSI = 0.145038
PSI_TO_KPA = 6.89476
BAR_TO_PSI = 14.5038

# Density
PPG_TO_KG_M3 = 119.826
KG_M3_TO_PPG = 1.0 / 119.826
SG_TO_PPG = 8.345

# Weight / Force
LBF_TO_N = 4.44822
KLBF_TO_KN = 4.44822
LBF_100FT2_TO_PA = 0.4788
PA_TO_LBF_100FT2 = 1.0 / 0.4788

# Torque
FTLB_TO_NM = 1.35582
FTLB_TO_KNM = 0.00135582

# Rheology
CP_TO_PAS = 1.0e-3
FANN_RPM_TO_SR = 1.703
RE_LAMINAR_MAX = 2100.0
RE_TURBULENT_MIN = 4000.0

# Angles
DEG_TO_RAD = 0.017453292519943295
RAD_TO_DEG = 57.29577951308232


# ═══════════════════════════════════════════════════════════════
#  ENGINEERING DEFAULTS
# ═══════════════════════════════════════════════════════════════

CD_BIT_DEFAULT = 0.95
PIPE_ROUGHNESS_IN_DEFAULT = 0.0018   # commercial steel (0.045 mm)

# Surge/Swab
CLINGING_COEF_A = 0.45
CLINGING_COEF_B = 0.55
TRIP_SPEED_MIN_FPS = 1.0
TRIP_SPEED_MAX_FPS = 15.0
SURGE_MARGIN_PPG = 0.5

# Cuttings
CUTTINGS_DENSITY_PPG = 21.7
CUTTINGS_D_REF_IN = 0.25
BED_HEIGHT_MAX_FRAC = 0.30
TRANSPORT_RATIO_MIN = 0.5
HOLE_CLEANING_EXPONENT = 0.4

# Gas
GAS_SG_METHANE = 0.55
GAS_SG_CO2 = 1.52
GAS_SG_H2S = 1.19
GAS_SG_DEFAULT = 0.65
GAS_SOLUBILITY_OBM_DEFAULT = 0.35
GAS_BUBBLE_RISE_FPS = 0.35
GAS_Z_DEFAULT = 0.9

# Losses
LOSS_SEEPAGE_MAX = 0.02
LOSS_PARTIAL_MAX = 0.10
LOSS_SEVERE_MAX = 0.50

# Ballooning
BALLOONING_PIT_GAIN_BBL = 5.0
BALLOONING_DECAY_MIN = 30.0

# Kick detection thresholds
KICK_FLOW_IMBALANCE_GPM = 15.0
KICK_PIT_GAIN_BBL = 5.0
KICK_CONNECTION_GAS_UNITS = 50.0
KICK_BG_GAS_UNITS = 20.0

# Events
NOZZLE_PLUG_MIN_FRAC = 0.10
NOZZLE_PLUG_SEVERE_FRAC = 0.35
BALLING_SPP_RISE_FRAC = 0.15
BALLING_TORQUE_RISE_FRAC = 0.20
BALLING_ROP_DROP_FRAC = 0.30
PACKOFF_SPP_RISE_FRAC = 0.25
PACKOFF_TORQUE_RISE_FRAC = 0.30
PACKOFF_DRAG_RISE_FRAC = 0.40
WASHOUT_SPP_DROP_FRAC = 0.10

# Pore pressure
MW_NORMAL_PPG = 8.65
OBG_DEFAULT_PPG = 18.0
EATON_EXP_DC = 1.2
EATON_EXP_SIGMA = 1.0
DC_MIN_VALID = 0.2
DC_MAX_VALID = 5.0

# Gas thresholds (pore pressure)
GAS_BG_BASELINE_MAX = 20.0
GAS_CG_SIGNIFICANT = 50.0
GAS_TG_SIGNIFICANT = 80.0
GAS_POG_SIGNIFICANT = 30.0

# GIF (Gas Influence Factor) bands — Kuwait
GIF_LOW_GAS_THRESHOLD = 30.0
GIF_MOD_GAS_THRESHOLD = 150.0
GIF_LOW_PPG = 0.05
GIF_MOD_PPG = 0.15
GIF_HIGH_PPG = 0.35


# ═══════════════════════════════════════════════════════════════
#  KUWAIT RA-0915 FORMATIONS (real field data)
# ═══════════════════════════════════════════════════════════════

# Format: (name, md_top_ft, tvd_top_ft, pp_ppg, fg_ppg, mw_used_ppg, notes)
KUWAIT_RA0915_FORMATIONS = [
    ("Zubair_top",       9209,  9209,  9.00, 16.50, 10.5, "Normal"),
    ("Zubair_mid",      10140, 10140, 10.50, 16.80, 12.2, "Increasing"),
    ("Zubair_base",     10550, 10550, 11.20, 17.20, 13.0, "High gas"),
    ("Ratawi_Shale",    10797, 10797, 11.85, 17.50, 13.7, "Dc+Sigma+Gas"),
    ("Ratawi_LS",       11185, 11185, 13.05, 17.80, 14.8, "Dc+Sigma"),
    ("Minagish",        11710, 11710, 14.00, 18.00, 15.6, "Dc+Sigma"),
    ("Makhul",          12729, 12729, 15.05, 18.20, 16.4, "High gas"),
    ("Hith",            13488, 13488, 17.40, 18.60, 18.3, "Trip gas"),
    ("Gotnia",          13980, 13980, 18.45, 18.90, 19.8, "Salt"),
    ("Najmah",          14426, 14426, 17.25, 18.50, 17.7, "Regression"),
    ("Sargelu",         14551, 14551, 16.70, 18.30, 17.5, "Regression"),
    ("Dharuma",         14678, 14678, 16.50, 18.30, 17.3, ""),
    ("Upper_Marrat",    15013, 15013, 16.10, 18.00, 17.1, "Drop"),
    ("Mid_Marrat_top",  15307, 14785, 12.50, 14.00, 13.0, "MPD"),
    ("Mid_Marrat_mid",  15655, 15530, 10.75, 12.50, 11.0, "MPD ECD"),
    ("Mid_Marrat_base", 15920, 15865,  9.40, 11.50,  9.6, "Near normal"),
]


# ═══════════════════════════════════════════════════════════════
#  LIVE CASE RA-0915 (23-Sep-2026)
# ═══════════════════════════════════════════════════════════════

LIVE_CASE_RA0915 = {
    "q_in_gpm":        199.3,
    "q_out_gpm":       201.0,
    "mw_in_ppg":       13.50,
    "mw_out_ppg":      10.69,
    "spp_psi":          47.5,
    "sbp_psi":          27.5,
    "pwd_bhp_psi":    9266.0,
    "pwd_ecd_ppg":      11.37,
    "tvd_ft":        15690.0,
    "mw_annulus_eff_ppg": 11.30,
}


# ═══════════════════════════════════════════════════════════════
#  TEMPERATURE CORRECTION DEFAULTS
# ═══════════════════════════════════════════════════════════════

K_TEMP_FACTOR_DEFAULT = 0.97
TAU_Y_TEMP_FACTOR_DEFAULT = 0.98
ANNULAR_MODEL_DEFAULT = "dodge_metzner"   # or "merlo"
