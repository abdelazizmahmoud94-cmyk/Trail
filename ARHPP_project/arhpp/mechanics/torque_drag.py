"""Torque & Drag Engine — full analysis across MD."""

import math
from typing import List, Optional

from arhpp.geometry.survey import md_to_tvd
from arhpp.mechanics.types import (
    TDConfig, TDInputs, TDResult, TDProfilePoint,
    BucklingType, OPERATION_PARAMS,
)
from arhpp.mechanics.buckling import BucklingEngine


DEG_TO_RAD = math.pi / 180.0


def _pipe_area_in2(od_in: float, id_in: float) -> float:
    return math.pi / 4.0 * (od_in ** 2 - id_in ** 2)


def _pipe_moment_of_inertia_in4(od_in: float, id_in: float) -> float:
    return math.pi / 64.0 * (od_in ** 4 - id_in ** 4)


def _pipe_polar_moment_in4(od_in: float, id_in: float) -> float:
    return math.pi / 32.0 * (od_in ** 4 - id_in ** 4)


def _weight_per_ft(od_in: float, id_in: float,
                     density_ppg: float = 65.5) -> float:
    area_in2 = _pipe_area_in2(od_in, id_in)
    lb_per_in2_ft = density_ppg * 12.0 / 231.0
    return area_in2 * lb_per_in2_ft


class TorqueDragEngine:
    def __init__(self, config: Optional[TDConfig] = None):
        self.config = config or TDConfig()
        self.buckling_engine = BucklingEngine(self.config)

    def compute(self, survey, bha_sections,
                 inputs: TDInputs,
                 hole_id_in: float = 8.5) -> TDResult:
        result = TDResult(operation=inputs.operation,
                            friction_factor=inputs.friction_factor)
        if not survey or not bha_sections:
            result.warnings.append("Empty survey or BHA")
            return result

        td_md = max(p.md for p in survey)
        step = max(self.config.step_size_ft, 10.0)
        n_steps = int(td_md / step) + 1

        if self.config.buoyancy_factor_enabled:
            bf = 1.0 - inputs.mud_weight_ppg / self.config.tubular_density_ppg
        else:
            bf = 1.0

        profile: List[TDProfilePoint] = []
        for i in range(n_steps + 1):
            md = min(i * step, td_md)
            p = TDProfilePoint(
                md_ft=md, tvd_ft=md_to_tvd(survey, md),
                inc_deg=self._interp_inc(survey, md),
                azi_deg=self._interp_azi(survey, md),
                dls=self._interp_dls(survey, md))
            profile.append(p)
        self._assign_bha(profile, bha_sections)

        op_params = OPERATION_PARAMS.get(inputs.operation, {})
        mu = inputs.friction_factor
        n = len(profile)
        if n < 2:
            result.profile = profile
            return result

        axial_tension_klb = -inputs.wob_klb
        torque_at_point = inputs.torque_at_bit_ftlb
        neutral_found = False

        for i in range(n - 1, 0, -1):
            p_up = profile[i - 1]
            p_dn = profile[i]
            L_ft = p_dn.md_ft - p_up.md_ft
            if L_ft <= 0:
                continue

            area_in2 = _pipe_area_in2(p_dn.od_in, p_dn.id_in)
            J_in4 = _pipe_polar_moment_in4(p_dn.od_in, p_dn.id_in)
            I_in4 = _pipe_moment_of_inertia_in4(p_dn.od_in, p_dn.id_in)
            w_air_lbft = _weight_per_ft(p_dn.od_in, p_dn.id_in)
            w_buoy_lbft = w_air_lbft * bf

            segment_weight_klb = w_buoy_lbft * L_ft / 1000.0
            inc_rad = p_dn.inc_deg * DEG_TO_RAD

            w_sin = w_buoy_lbft * math.sin(inc_rad)
            dls_rad_per_ft = p_dn.dls * DEG_TO_RAD / 100.0
            tension_curv = axial_tension_klb * 1000.0 * dls_rad_per_ft
            side_force_lbft = abs(w_sin) + abs(tension_curv)

            # Tool joint drag correction
            tj_factor = 1.0
            if self.config.tool_joint_drag_enabled:
                tj_len_frac = (
                    self.config.tool_joint_diameter_increase /
                    self.config.tool_joint_spacing_ft / 12.0)
                tj_factor = 1.0 + 8.0 * tj_len_frac
            side_force_lbft *= tj_factor
            p_dn.side_force_lbft = side_force_lbft

            drag_klb = mu * side_force_lbft * L_ft / 1000.0
            p_dn.drag_klb = drag_klb

            drag_sign = op_params.get("drag_sign", 0.0)
            if drag_sign > 0:
                axial_change = segment_weight_klb + drag_klb
            elif drag_sign < 0:
                axial_change = segment_weight_klb - drag_klb
            else:
                axial_change = segment_weight_klb

            axial_tension_klb += axial_change
            p_dn.axial_tension_klb = max(0.0, axial_tension_klb)
            p_dn.axial_compression_klb = max(0.0, -axial_tension_klb)

            if not neutral_found and axial_tension_klb >= 0:
                p_dn.is_neutral_point = True
                result.neutral_point_md_ft = p_dn.md_ft
                neutral_found = True

            if op_params.get("rotation", False):
                friction_torque_ftlb = (
                    mu * side_force_lbft * L_ft *
                    (p_dn.od_in / 2.0) / 12.0)
                torque_at_point += friction_torque_ftlb
            p_dn.torque_ftlb = torque_at_point

            if area_in2 > 0:
                p_dn.tensile_stress_psi = (
                    abs(axial_tension_klb) * 1000.0 / area_in2)
            if J_in4 > 0:
                tau_torsion = ((torque_at_point * 12.0)
                                 * (p_dn.od_in / 2.0) / J_in4)
            else:
                tau_torsion = 0.0
            if I_in4 > 0:
                curvature = p_dn.dls * DEG_TO_RAD / (100.0 * 12.0)
                p_dn.bending_stress_psi = (
                    self.config.tubular_youngs_psi * curvature
                    * (p_dn.od_in / 2.0))
            sigma_a = p_dn.tensile_stress_psi
            sigma_b = p_dn.bending_stress_psi
            p_dn.von_mises_psi = math.sqrt(
                sigma_a ** 2 + sigma_b ** 2 - sigma_a * sigma_b
                + 3.0 * tau_torsion ** 2)

            bk = self.buckling_engine.check_buckling(
                od_in=p_dn.od_in, id_in=p_dn.id_in,
                inc_deg=p_dn.inc_deg, dls=p_dn.dls,
                axial_load_klb=-axial_tension_klb,
                mw_ppg=inputs.mud_weight_ppg,
                hole_id_in=hole_id_in)
            p_dn.buckling = bk.buckling_type
            p_dn.buckling_margin_klb = (
                bk.sinusoidal_threshold_klb - max(0.0, -axial_tension_klb))

        result.profile = profile
        if profile:
            top = profile[0]
            result.hookload_klb = (top.axial_tension_klb
                                     + self.config.block_weight_klb
                                     + inputs.block_weight_klb)
            result.surface_torque_ftlb = top.torque_ftlb
            result.max_von_mises_psi = max(
                p.von_mises_psi for p in profile)
            result.max_contact_force_klb = max(
                (p.side_force_lbft * step / 1000.0) for p in profile)
            result.total_drag_klb = sum(p.drag_klb for p in profile)
            for p in profile:
                if p.buckling == BucklingType.HELICAL:
                    result.buckling_status = BucklingType.HELICAL
                    break
                elif p.buckling == BucklingType.SINUSOIDAL:
                    result.buckling_status = BucklingType.SINUSOIDAL
        return result

    @staticmethod
    def _interp_inc(survey, md):
        if not survey:
            return 0.0
        if md <= survey[0].md:
            return survey[0].inc
        if md >= survey[-1].md:
            return survey[-1].inc
        for i in range(1, len(survey)):
            if survey[i].md >= md:
                a, b = survey[i - 1], survey[i]
                if b.md == a.md:
                    return b.inc
                f = (md - a.md) / (b.md - a.md)
                return a.inc + f * (b.inc - a.inc)
        return survey[-1].inc

    @staticmethod
    def _interp_azi(survey, md):
        if not survey:
            return 0.0
        if md <= survey[0].md:
            return survey[0].azi
        if md >= survey[-1].md:
            return survey[-1].azi
        for i in range(1, len(survey)):
            if survey[i].md >= md:
                a, b = survey[i - 1], survey[i]
                if b.md == a.md:
                    return b.azi
                f = (md - a.md) / (b.md - a.md)
                return a.azi + f * (b.azi - a.azi)
        return survey[-1].azi

    @staticmethod
    def _interp_dls(survey, md):
        if not survey:
            return 0.0
        for i in range(1, len(survey)):
            if survey[i].md >= md:
                return survey[i].dls
        return survey[-1].dls if survey else 0.0

    def _assign_bha(self, profile, bha_sections):
        for p in profile:
            for sec in bha_sections:
                if sec.top_md <= p.md_ft <= sec.bottom_md:
                    p.od_in = sec.od_in
                    p.id_in = sec.id_in
                    p.component = sec.name
                    break
            else:
                if bha_sections:
                    p.od_in = bha_sections[0].od_in
                    p.id_in = bha_sections[0].id_in
                    p.component = bha_sections[0].name
