from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class UnitType:
    name: str
    count: int
    carpet_area_m2: float

@dataclass
class RegulatoryInputs:
    plot_area_m2: float | None = None
    plot_width_m: float | None = None
    plot_depth_m: float | None = None
    road_width_m: float | None = None
    permissible_fsi: float | None = None
    maximum_fsi: float | None = None
    permissible_built_up_area_m2: float | None = None
    maximum_built_up_area_m2: float | None = None
    maximum_height_m: float | None = None
    front_setback_m: float | None = None
    rear_setback_m: float | None = None
    side_setback_left_m: float | None = None
    side_setback_right_m: float | None = None
    minimum_open_space_m2: float | None = None
    recreational_open_space_m2: float | None = None
    amenity_space_m2: float | None = None
    car_parking_required: int | None = None
    two_wheeler_parking_required: int | None = None
    visitor_parking_required: Any = None
    fire_access_required: bool | None = None
    fire_lift_required: bool | None = None
    fire_lift_count: int | None = None
    fire_staircase_required: bool | None = None
    staircase_count: int | None = None
    staircase_width_m: float | None = None
    corridor_width_m: float | None = None
    lift_required: bool | None = None
    lift_count: int | None = None
    accessible_entrance_required: bool | None = None
    refuge_area_required: Any = None
    building_separation_m: float | None = None

@dataclass
class DesignPreferences:
    floor_height_m: float = 3.0
    parking_floor_height_m: float = 2.4
    requested_units: int | None = None
    requested_buildings: int | None = None
    allow_basement: bool = True
    allow_podium: bool = True
    allow_stilt: bool = True
    maximize_fsi: bool = True
    maximize_usable_area: bool = True
    maximize_parking: bool = True
    optimize_daylight: bool = True
    optimize_ventilation: bool = True
    preferred_orientation: Any = None

@dataclass
class SiteGeometry:
    plot_area_m2: float | None
    boundary: Any = None
    plot_width_m: float | None = None
    plot_depth_m: float | None = None
    north_direction: Any = None
    road_width_m: float | None = None

@dataclass
class BuildingDesign:
    building_id: str
    floor_count: int
    floor_height_m: float
    footprint_m2: float
    floor_plate_m2: float
    total_floor_area_m2: float
    units: list[UnitType] = field(default_factory=list)
    lift_count: int = 0
    staircase_count: int = 0
    corridor_area_m2: float = 0.0
    core_area_m2: float = 0.0

@dataclass
class ParkingDesign:
    car_spaces: int
    two_wheeler_spaces: int
    visitor_spaces: int = 0
    car_bay_area_m2: float = 0.0
    two_wheeler_bay_area_m2: float = 0.0
    circulation_area_m2: float = 0.0
    total_area_m2: float = 0.0
    strategy: str = "surface"

@dataclass
class DesignSpecification:
    site: SiteGeometry
    regulatory: RegulatoryInputs
    preferences: DesignPreferences
    buildings: list[BuildingDesign] = field(default_factory=list)
    parking: ParkingDesign | None = None
    open_space_area_m2: float = 0.0
    amenity_area_m2: float = 0.0
    total_built_up_area_m2: float = 0.0
    fsi_used: float = 0.0
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)
