"""Dynamic ECD/ESD helpers."""

from arhpp.core.constants import PSI_PER_FT_PER_PPG


def compute_ecd(bhp_psi: float, tvd_ft: float) -> float:
    if tvd_ft <= 0:
        return 0.0
    return bhp_psi / (PSI_PER_FT_PER_PPG * tvd_ft)


def compute_esd(hydrostatic_psi: float, surge_psi: float,
                  swab_psi: float, tvd_ft: float) -> float:
    if tvd_ft <= 0:
        return 0.0
    p = hydrostatic_psi + surge_psi - swab_psi
    return p / (PSI_PER_FT_PER_PPG * tvd_ft)
