"""Cuttings Transport Engine — slip, transport ratio, bed, extra ECD."""

import math
from dataclasses import dataclass, field
from typing import List

from arhpp.core.constants import (
    CUTTINGS_DENSITY_PPG, CUTTINGS_D_REF_IN,
    BED_HEIGHT_MAX_FRAC, TRANSPORT_RATIO_MIN, PSI_PER_FT_PER_PPG,
)


@dataclass
class CuttingsSectionResult:
    top_md: float = 0.0
    bottom_md: float = 0.0
    length_ft: float = 0.0
    hole_id_in: float = 0.0
    pipe_od_in: float = 0.0
    inclination_deg: float = 0.0
    ann_velocity_fps: float = 0.0
    slip_velocity_fps: float = 0.0
    transport_ratio: float = 0.0
    cuttings_conc_vol: float = 0.0
    bed_height_frac: float = 0.0
    extra_dp_psi: float = 0.0
    mw_effective_ppg: float = 0.0


@dataclass
class CuttingsResult:
    rop_ft_hr: float = 0.0
    rpm: float = 0.0
    q_gpm: float = 0.0
    cuttings_rate_lb_hr: float = 0.0
    cuttings_rate_bbl_hr: float = 0.0
    total_extra_dp_psi: float = 0.0
    total_extra_ecd_ppg: float = 0.0
    peak_bed_frac: float = 0.0
    sections: List[CuttingsSectionResult] = field(default_factory=list)


def _inc_at_md(survey, md: float) -> float:
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


def slip_velocity_moore(d_cut_in: float, rho_cut_ppg: float,
                          mw_ppg: float, n: float, k: float) -> float:
    """Moore's slip velocity (ft/s)."""
    mu_a = max(1.0, k * 100.0)
    drho = max(rho_cut_ppg - mw_ppg, 0.5)
    vs = (175.0 * d_cut_in * (drho ** 0.667)
          / ((mw_ppg ** 0.333) * (mu_a ** 0.333)))
    return max(0.1, min(vs, 20.0))


def cuttings_concentration(rop_ft_hr: float, hid_in: float,
                             od_in: float, v_fps: float) -> float:
    if v_fps <= 0 or hid_in <= od_in:
        return 1.0
    rop_fps = rop_ft_hr / 3600.0
    num = rop_fps * (hid_in ** 2)
    den = v_fps * (hid_in ** 2 - od_in ** 2)
    if den <= 0:
        return 1.0
    return min(0.5, num / den)


def bed_height_fraction(tr: float, inc_deg: float) -> float:
    if tr >= TRANSPORT_RATIO_MIN:
        return 0.0
    deficit = (TRANSPORT_RATIO_MIN - tr) / TRANSPORT_RATIO_MIN
    inc_f = 1.0 + 0.8 * math.sin(math.radians(abs(inc_deg)))
    return min(BED_HEIGHT_MAX_FRAC, deficit * 0.4 * inc_f)


def extra_friction_from_bed(bed_frac: float, hid: float,
                              od: float, length_ft: float,
                              mw: float, v_fps: float) -> float:
    if bed_frac <= 0:
        return 0.0
    a_ratio = 1.0 / max(0.4, 1.0 - bed_frac * 0.6)
    dp_base = 0.0001 * mw * (v_fps ** 2) * length_ft
    return dp_base * (a_ratio - 1.0)


def compute_cuttings_transport(rop_ft_hr: float, rpm: float,
                                 q_gpm: float, hole_sections,
                                 bha_sections, annulus_col, survey,
                                 step_ft: float = 30.0,
                                 d_cut_in: float = CUTTINGS_D_REF_IN,
                                 rho_cut_ppg: float = CUTTINGS_DENSITY_PPG
                                 ) -> CuttingsResult:
    from arhpp.geometry.well_geometry import effective_hole_id
    from arhpp.geometry.bha import string_od_at_md

    res = CuttingsResult(rop_ft_hr=rop_ft_hr, rpm=rpm, q_gpm=q_gpm)
    if not hole_sections:
        return res

    hid_td = hole_sections[-1].hole_id_in
    a_hole = math.pi / 4.0 * hid_td ** 2
    rho_lb_in3 = rho_cut_ppg / 231.0
    res.cuttings_rate_lb_hr = rop_ft_hr * 12.0 * a_hole * rho_lb_in3
    res.cuttings_rate_bbl_hr = rop_ft_hr * 12.0 * a_hole / 9702.0

    if not annulus_col.segments:
        return res

    total = 0.0
    peak = 0.0
    for seg in annulus_col.segments:
        md = seg.top_md
        bot = seg.bottom_md
        while md < bot:
            nxt = min(md + step_ft, bot)
            mid = 0.5 * (md + nxt)
            hid = effective_hole_id(hole_sections, mid)
            od = string_od_at_md(bha_sections, mid)
            if hid > od > 0 and q_gpm > 0:
                area = math.pi / 4.0 * (hid ** 2 - od ** 2)
                v = (q_gpm * 0.002228 * 144.0) / area
                inc = _inc_at_md(survey, mid)
                vs = slip_velocity_moore(
                    d_cut_in, rho_cut_ppg, seg.mw, seg.n, seg.k)
                rpm_f = 1.0 - 0.15 * math.sqrt(max(0.0, rpm) / 100.0)
                vs *= max(0.4, rpm_f)
                tr = max(0.0, (v - vs) / v) if v > 0 else 0.0
                cc = cuttings_concentration(rop_ft_hr, hid, od, v)
                bed = bed_height_fraction(tr, inc)
                dp_ex = extra_friction_from_bed(
                    bed, hid, od, nxt - md, seg.mw, v)
                row = CuttingsSectionResult(
                    md, nxt, nxt - md, hid, od, inc,
                    v, vs, tr, cc, bed, dp_ex)
                row.mw_effective_ppg = seg.mw * (1.0 - cc) + rho_cut_ppg * cc
                res.sections.append(row)
                total += dp_ex
                peak = max(peak, bed)
            md = nxt

    res.total_extra_dp_psi = total
    res.peak_bed_frac = peak
    tvd_ref = (annulus_col.segments[-1].bottom_tvd
               if annulus_col.segments else 0.0)
    if tvd_ref > 0:
        res.total_extra_ecd_ppg = total / (PSI_PER_FT_PER_PPG * tvd_ref)
    return res
