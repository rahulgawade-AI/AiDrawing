from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SiteConstraints:
    """
    Physical/site constraints used by the building-design engine.

    Image-derived physical values should be preferred over user supplied
    values when the image mapper detected them.
    """

    plot_area_m2: Optional[float] = None
    plot_width_m: Optional[float] = None
    plot_depth_m: Optional[float] = None
    plot_shape: Optional[str] = None

    plot_side_lengths_m: Dict[str, float] = field(default_factory=dict)

    survey_number: Optional[str] = None
    plot_number: Optional[str] = None

    road_width_m: Optional[float] = None
    road_widths_m: List[float] = field(default_factory=list)
    road_name: Optional[str] = None
    road_frontage_count: Optional[int] = None

    access_width_m: Optional[float] = None

    north_direction: Optional[str] = None
    scale: Optional[str] = None


@dataclass
class FSIConstraints:
    """
    Regulatory FSI/development-potential information interpreted from the
    existing PostgreSQL resolver output.

    This class does NOT modify the resolver.
    """

    permissible_fsi: Optional[float] = None
    maximum_fsi: Optional[float] = None

    basic_fsi: Optional[float] = None
    premium_fsi: Optional[float] = None
    maximum_tdr_loading: Optional[float] = None

    maximum_building_potential: Optional[float] = None
    permissible_floor_area_m2: Optional[float] = None

    basis: Optional[str] = None

    source_rule_ids: List[str] = field(default_factory=list)


@dataclass
class HeightConstraints:

    maximum_height_m: Optional[float] = None
    requested_height_m: Optional[float] = None
    requested_floors: Optional[int] = None

    floor_height_assumption_m: Optional[float] = None

    source_rule_ids: List[str] = field(default_factory=list)


@dataclass
class SetbackConstraints:

    front_m: Optional[float] = None
    rear_m: Optional[float] = None
    side1_m: Optional[float] = None
    side2_m: Optional[float] = None

    minimum_m: Optional[float] = None

    source_rule_ids: List[str] = field(default_factory=list)

    status: str = "NOT_RESOLVED"


@dataclass
class ParkingConstraints:

    required_spaces: Optional[float] = None

    parking_mode: Optional[str] = None

    requested_units: Optional[int] = None

    unit_mix: List[Dict[str, Any]] = field(default_factory=list)

    source_rule_ids: List[str] = field(default_factory=list)

    status: str = "NOT_RESOLVED"


@dataclass
class AccessConstraints:

    road_width_m: Optional[float] = None
    access_width_m: Optional[float] = None

    fire_access_required: Optional[bool] = None

    source_rule_ids: List[str] = field(default_factory=list)


@dataclass
class BuildingProgram:

    project_type: Optional[str] = None
    development_type: Optional[str] = None

    building_use: Optional[str] = None
    building_type: Optional[str] = None
    occupancy_type: Optional[str] = None

    requested_units: Optional[int] = None

    requested_unit_mix: List[Dict[str, Any]] = field(
        default_factory=list
    )

    requested_unit_area: Dict[str, Any] = field(
        default_factory=dict
    )

    allow_stilt_parking: Optional[bool] = None
    avoid_basement: Optional[bool] = None


@dataclass
class DesignObjectives:

    maximize_fsi: Optional[bool] = None
    maximize_parking: Optional[bool] = None
    maximize_usable_area: Optional[bool] = None

    optimize_daylight: Optional[bool] = None
    optimize_ventilation: Optional[bool] = None
    optimize_orientation: Optional[bool] = None

    preferred_orientation: Optional[str] = None

    design_objective: Optional[str] = None


@dataclass
class DesignConstraints:
    """
    Complete contract passed from planning phase to design phase.
    """

    site: SiteConstraints

    program: BuildingProgram

    fsi: FSIConstraints

    height: HeightConstraints

    setbacks: SetbackConstraints

    parking: ParkingConstraints

    access: AccessConstraints

    objectives: DesignObjectives

    regulatory_rules: List[Dict[str, Any]] = field(
        default_factory=list
    )

    unresolved_constraints: List[str] = field(
        default_factory=list
    )

    warnings: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)