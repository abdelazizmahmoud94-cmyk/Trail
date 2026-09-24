"""Data types for Mechanics Engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class OperationType(str, Enum):
    ROT_OFF_BOTTOM = "rot_off_bottom"
    RUNNING_IN = "running_in"
    PULLING_OUT = "pulling_out"
    DRILLING_ROTARY = "drilling_rotary"
    DRILLING_SLIDING = "drilling_sliding"
    REAMING = "reaming"
    BACKREAMING = "backreaming"
    PICK_UP = "pick_up"
    SLACK_OFF = "slack_off"
    UNDERREAMING = "underreaming"
    CUTTING = "cutting"
    CUSTOM_UP = "custom_up"
    CUSTOM_DOWN = "custom_down"
    CUSTOM_STATIONARY = "custom_stationary"


class BucklingType(str, Enum):
    NONE = "none"
    SINUSOIDAL = "sinusoidal"
    HELICAL = "helical"


@dataclass
class RigLimits:
    rig_hoisting_limit_klb: float = 750.0
    max_rig_torque_ftlb: float = 25000.0
    rig_torque_setting_ftlb: float = 22000.0
    max_makeup_torque_ftlb: float = 30000.0
    top_drive_limit_ftlb: float = 30000.0
    string_yield_klb: float = 550.0
    connection_yield_klb: float = 480.0


@dataclass
class TDConfig:
    friction_factor_cased: float = 0.20
    friction_factor_open: float = 0.30
    friction_factor_rotating: float = 0.15
    friction_factor_sliding: float = 0.35
    buoyancy_factor_enabled: bool = True
    side_wall_stiffness: float = 1.0
    include_contact_force: bool = True
    tubular_density_ppg: float = 65.5
    tubular_youngs_psi: float = 30e6
    tubular_poisson: float = 0.28
    rkb_to_msl_ft: float = 55.0
    block_weight_klb: float = 0.0
    step_size_ft: float = 30.0
    torque_drag_weight: float = 0.5
    tool_joint_drag_enabled: bool = True
    tool_joint_diameter_increase: float = 0.125
    tool_joint_spacing_ft: float = 30.0


@dataclass
class TDProfilePoint:
    md_ft: float = 0.0
    tvd_ft: float = 0.0
    inc_deg: float = 0.0
    azi_deg: float = 0.0
    dls: float = 0.0
    axial_tension_klb: float = 0.0
    axial_compression_klb: float = 0.0
    torque_ftlb: float = 0.0
    von_mises_psi: float = 0.0
    bending_stress_psi: float = 0.0
    tensile_stress_psi: float = 0.0
    side_force_lbft: float = 0.0
    contact_force_klb: float = 0.0
    drag_klb: float = 0.0
    buckling: BucklingType = BucklingType.NONE
    buckling_margin_klb: float = 0.0
    is_neutral_point: bool = False
    component: str = ""
    od_in: float = 0.0
    id_in: float = 0.0


@dataclass
class TDInputs:
    operation: OperationType = OperationType.DRILLING_ROTARY
    friction_factor: float = 0.25
    wob_klb: float = 0.0
    rpm: float = 0.0
    torque_at_bit_ftlb: float = 0.0
    block_weight_klb: float = 0.0
    mud_weight_ppg: float = 12.0
    tvd_ft: float = 15000.0


@dataclass
class TDResult:
    operation: OperationType = OperationType.DRILLING_ROTARY
    friction_factor: float = 0.0
    hookload_klb: float = 0.0
    surface_torque_ftlb: float = 0.0
    max_von_mises_psi: float = 0.0
    max_contact_force_klb: float = 0.0
    max_bending_moment_ftlb: float = 0.0
    total_drag_klb: float = 0.0
    neutral_point_md_ft: float = 0.0
    sinusoidal_buckling_klb: float = 0.0
    helical_buckling_klb: float = 0.0
    buckling_status: BucklingType = BucklingType.NONE
    hoisting_ok: bool = True
    torque_ok: bool = True
    yield_ok: bool = True
    profile: List[TDProfilePoint] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


OPERATION_PARAMS = {
    OperationType.ROT_OFF_BOTTOM: {"drag_sign": +1.0, "rotation": True, "rpm_factor": 0.5},
    OperationType.RUNNING_IN: {"drag_sign": -1.0, "rotation": False},
    OperationType.PULLING_OUT: {"drag_sign": +1.0, "rotation": False},
    OperationType.DRILLING_ROTARY: {"drag_sign": 0.0, "rotation": True, "rpm_factor": 1.0},
    OperationType.DRILLING_SLIDING: {"drag_sign": -1.0, "rotation": False},
    OperationType.REAMING: {"drag_sign": +1.0, "rotation": True, "rpm_factor": 0.8},
    OperationType.BACKREAMING: {"drag_sign": +1.0, "rotation": True, "rpm_factor": 0.8},
    OperationType.PICK_UP: {"drag_sign": +1.0, "rotation": False},
    OperationType.SLACK_OFF: {"drag_sign": -1.0, "rotation": False},
    OperationType.UNDERREAMING: {"drag_sign": +1.0, "rotation": True},
    OperationType.CUTTING: {"drag_sign": 0.0, "rotation": True},
    OperationType.CUSTOM_UP: {"drag_sign": +1.0, "rotation": False},
    OperationType.CUSTOM_DOWN: {"drag_sign": -1.0, "rotation": False},
    OperationType.CUSTOM_STATIONARY: {"drag_sign": 0.0, "rotation": False},
}
