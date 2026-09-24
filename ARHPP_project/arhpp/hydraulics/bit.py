"""Bit Hydraulics Engine — dP, jet velocity, HHP, HSI, impact force."""

import math
from dataclasses import dataclass
from typing import List

from arhpp.core.constants import CD_BIT_DEFAULT


@dataclass
class Nozzle:
    size_32nd_in: float
    tfa_in2: float = 0.0

    def area_in2(self) -> float:
        if self.tfa_in2 > 0:
            return self.tfa_in2
        d_in = self.size_32nd_in / 32.0
        return math.pi / 4.0 * d_in ** 2


@dataclass
class BitResult:
    tfa_in2: float = 0.0
    dp_psi: float = 0.0
    jet_velocity_fps: float = 0.0
    hhp_hp: float = 0.0
    hsi: float = 0.0
    impact_force_lbf: float = 0.0


def total_flow_area(nozzles: List[Nozzle]) -> float:
    return sum(n.area_in2() for n in nozzles if n.size_32nd_in > 0)


def bit_pressure_drop(q_gpm: float, nozzles: List[Nozzle],
                        mw_ppg: float, bit_diameter_in: float = 8.5,
                        cd: float = CD_BIT_DEFAULT) -> BitResult:
    """
    Field formula: dP[psi] = rho[ppg] * Q^2[gpm] / (12032 * Cd^2 * TFA^2[in2])
    """
    r = BitResult()
    tfa = total_flow_area(nozzles)
    r.tfa_in2 = tfa
    if tfa <= 0 or q_gpm <= 0:
        return r

    r.dp_psi = (mw_ppg * q_gpm * q_gpm) / (
        12032.0 * cd * cd * tfa * tfa)
    r.jet_velocity_fps = q_gpm / (3.117 * cd * tfa)
    r.hhp_hp = r.dp_psi * q_gpm / 1714.0

    bit_area = math.pi / 4.0 * bit_diameter_in ** 2
    r.hsi = r.hhp_hp / bit_area if bit_area > 0 else 0.0
    r.impact_force_lbf = mw_ppg * q_gpm * r.jet_velocity_fps / 1930.0
    return r
