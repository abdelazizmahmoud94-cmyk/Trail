"""WITS Tag Mapper."""

import re
from dataclasses import dataclass, field
from typing import Dict, Optional


WITS_IN_MAP: Dict[str, str] = {
    "0108": "bit_depth_ft",
    "0110": "hole_depth_ft",
    "0112": "block_position_ft",
    "0113": "rop_ft_hr",
    "0114": "hookload_klb",
    "0116": "wob_klb",
    "0118": "torque_ftlb",
    "0120": "rpm",
    "0121": "rotary_speed_rpm",
    "0122": "standpipe_pressure_psi",
    "0124": "casing_pressure_psi",
    "0127": "mud_flow_out_gpm",
    "0128": "mud_flow_in_gpm",
    "0129": "mud_pit_volume_bbl",
    "0130": "mud_pit_gain_bbl",
    "0132": "mud_temperature_in_f",
    "0134": "mud_temperature_out_f",
    "0135": "mud_temperature_out_f",
    "0136": "mud_weight_in_ppg",
    "0138": "mud_weight_out_ppg",
    "0141": "gas_total_units",
    "0142": "gas_background_units",
    "0143": "gas_connection_units",
    "0144": "gas_trip_units",
    "0145": "gas_pump_off_units",
    "0147": "choke_position_pct",
    "0148": "choke_position_a_pct",
    "0149": "choke_position_b_pct",
    "0150": "surface_back_pressure_psi",
    "0151": "wellhead_pressure_psi",
    "0152": "casing_pressure_psi",
    "0153": "kill_line_pressure_psi",
    "0154": "pump_stroke_rate_spm",
    "0155": "pump_stroke_total",
    "0157": "pump_pressure_psi",
    "0158": "standpipe_pressure_psi",
    "0159": "mud_flow_out_percent",
    "0835": "bottom_hole_temperature_f",
    "0913": "pwd_bhp_psi",
    "0914": "pwd_annular_pressure_psi",
    "0915": "pwd_ecd_ppg",
    "0916": "pwd_internal_pressure_psi",
    "0917": "pwd_temperature_f",
    "0918": "bap_diff_pressure_psi",
    "0201": "bit_depth_m",
    "0202": "hole_depth_m",
    "0203": "rop_m_hr",
}


WITS_OUT_MAP: Dict[str, str] = {
    "0150": "surface_back_pressure_psi",
    "0151": "wellhead_pressure_psi",
    "0913": "bhp_psi",
    "0915": "ecd_ppg",
}


@dataclass
class WITSRecord:
    record_type: str = "01"
    timestamp: str = ""
    well_id: str = ""
    site_id: str = ""
    fields: Dict[str, float] = field(default_factory=dict)
    raw_tags: Dict[str, str] = field(default_factory=dict)


def parse_wits_line(line: str) -> Optional[WITSRecord]:
    if not line or not line.strip():
        return None
    line = line.strip()
    rec = WITSRecord()
    tokens = re.findall(r"(\d{4})\s*[:=]?\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)",
                          line)
    if not tokens:
        return None
    for tag, value in tokens:
        try:
            v = float(value)
        except ValueError:
            continue
        rec.raw_tags[tag] = value
        field_name = WITS_IN_MAP.get(tag)
        if field_name:
            rec.fields[field_name] = v
    return rec if rec.fields else None


def to_arhpp_inputs(rec: WITSRecord) -> Dict[str, float]:
    out = {}
    f = rec.fields
    if "bit_depth_ft" in f: out["bit_md_ft"] = f["bit_depth_ft"]
    if "hole_depth_ft" in f: out["hole_md_ft"] = f["hole_depth_ft"]
    if "rop_ft_hr" in f: out["rop_ft_hr"] = f["rop_ft_hr"]
    if "wob_klb" in f: out["wob_klb"] = f["wob_klb"]
    if "torque_ftlb" in f: out["torque_ftlb"] = f["torque_ftlb"]
    if "rpm" in f: out["rpm"] = f["rpm"]
    if "standpipe_pressure_psi" in f:
        out["spp_psi"] = f["standpipe_pressure_psi"]
    if "mud_flow_in_gpm" in f: out["q_in_gpm"] = f["mud_flow_in_gpm"]
    if "mud_flow_out_gpm" in f: out["q_out_gpm"] = f["mud_flow_out_gpm"]
    if "surface_back_pressure_psi" in f:
        out["sbp_psi"] = f["surface_back_pressure_psi"]
    if "wellhead_pressure_psi" in f:
        out["wellhead_pressure_psi"] = f["wellhead_pressure_psi"]
    if "mud_weight_in_ppg" in f: out["mw_in_ppg"] = f["mud_weight_in_ppg"]
    if "mud_weight_out_ppg" in f: out["mw_out_ppg"] = f["mud_weight_out_ppg"]
    if "mud_temperature_in_f" in f:
        out["temp_in_f"] = f["mud_temperature_in_f"]
    if "mud_temperature_out_f" in f:
        out["temp_out_f"] = f["mud_temperature_out_f"]
    if "mud_pit_volume_bbl" in f:
        out["pit_volume_bbl"] = f["mud_pit_volume_bbl"]
    if "mud_pit_gain_bbl" in f:
        out["pit_gain_bbl"] = f["mud_pit_gain_bbl"]
    if "gas_total_units" in f: out["gas_total"] = f["gas_total_units"]
    if "gas_background_units" in f:
        out["gas_bg"] = f["gas_background_units"]
    if "gas_connection_units" in f:
        out["gas_cg"] = f["gas_connection_units"]
    if "gas_trip_units" in f: out["gas_tg"] = f["gas_trip_units"]
    if "gas_pump_off_units" in f: out["gas_pog"] = f["gas_pump_off_units"]
    if "pwd_bhp_psi" in f: out["pwd_bhp_psi"] = f["pwd_bhp_psi"]
    if "pwd_ecd_ppg" in f: out["pwd_ecd_ppg"] = f["pwd_ecd_ppg"]
    if "pwd_temperature_f" in f:
        out["pwd_temp_f"] = f["pwd_temperature_f"]
    if "bap_diff_pressure_psi" in f:
        out["bap_diff_pressure_psi"] = f["bap_diff_pressure_psi"]
    if "choke_position_a_pct" in f:
        out["choke_a_pct"] = f["choke_position_a_pct"]
    if "choke_position_b_pct" in f:
        out["choke_b_pct"] = f["choke_position_b_pct"]
    return out


def to_wits_out_line(channels: Dict[str, float]) -> str:
    parts = []
    for tag, field in WITS_OUT_MAP.items():
        if field in channels:
            v = channels[field]
            parts.append(f"{tag} {v:.4f}")
    return " ".join(parts) + "\r\n"
