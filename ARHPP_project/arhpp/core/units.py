"""ARHPP — Unit helpers. All petroleum units: ft, in, bbl, psi, ppg, cP."""

import math
from arhpp.core.constants import (
    PSI_PER_FT_PER_PPG,
    BBL_PER_FT_CONST,
)


def ppg_to_gradient(mw_ppg: float) -> float:
    """ppg -> psi/ft."""
    return PSI_PER_FT_PER_PPG * mw_ppg


def gradient_to_ppg(gradient_psi_ft: float) -> float:
    """psi/ft -> ppg."""
    if PSI_PER_FT_PER_PPG <= 0:
        return 0.0
    return gradient_psi_ft / PSI_PER_FT_PER_PPG


def annulus_capacity_bblft(hole_id_in: float, pipe_od_in: float) -> float:
    """Annular capacity in bbl/ft: (ID² - OD²)/1029.4."""
    if hole_id_in <= 0 or pipe_od_in < 0:
        return 0.0
    if hole_id_in <= pipe_od_in:
        return 0.0
    return (hole_id_in ** 2 - pipe_od_in ** 2) / BBL_PER_FT_CONST


def pipe_capacity_bblft(pipe_id_in: float) -> float:
    """Pipe internal capacity in bbl/ft: ID²/1029.4."""
    if pipe_id_in <= 0:
        return 0.0
    return (pipe_id_in ** 2) / BBL_PER_FT_CONST


def pipe_displacement_bblft(od_in: float, id_in: float) -> float:
    """Steel displacement bbl/ft: (OD² - ID²)/1029.4."""
    if od_in <= id_in or od_in <= 0:
        return 0.0
    return (od_in ** 2 - id_in ** 2) / BBL_PER_FT_CONST


def deg_to_rad(deg: float) -> float:
    return deg * math.pi / 180.0


def rad_to_deg(rad: float) -> float:
    return rad * 180.0 / math.pi
