from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)


@dataclass
class PlanningFactContext:
    """
    Facts describing the current planning/site scenario.

    This class contains facts only.

    It does NOT:
        - evaluate UDCPR rules
        - calculate FSI
        - calculate setbacks
        - generate buildings
        - perform optimization

    It acts as the broader input/context model and can be
    converted into canonical PlanningFacts for regulatory
    evaluation.
    """

    # ==========================================================
    # PROJECT
    # ==========================================================

    project_id: str | None = None

    project_type: str | None = None

    development_type: str | None = None

    # ==========================================================
    # SITE
    # ==========================================================

    plot_area: float | None = None

    plot_number: str | None = None

    boundary: Any | None = None

    north_direction: float | None = None

    plot_shape: str | None = None

    # ==========================================================
    # ROAD / ACCESS
    # ==========================================================

    road_width: float | None = None

    road_type: str | None = None

    road_name: str | None = None

    road_classification: str | None = None

    access_available: bool | None = None

    road_widths: list[float] = field(
        default_factory=list
    )

    road_frontage_count: int = 0

    road_locations: list[str] = field(
        default_factory=list
    )

    # ==========================================================
    # LOCATION
    # ==========================================================

    latitude: float | None = None

    longitude: float | None = None

    location: str | None = None

    village: str | None = None

    city: str | None = None

    district: str | None = None

    state: str | None = None

    # ==========================================================
    # PLANNING AUTHORITY
    # ==========================================================

    planning_authority: str | None = None

    development_authority: str | None = None

    municipality: str | None = None

    # ==========================================================
    # ZONING
    # ==========================================================

    zone_type: str | None = None

    land_use_zone: str | None = None

    land_use_classification: str | None = None

    congested_area: bool | None = None

    # ==========================================================
    # SPECIAL ZONES / RESTRICTIONS
    # ==========================================================

    tod_zone: bool | None = None

    heritage_zone: bool | None = None

    crz_zone: bool | None = None

    eco_sensitive_zone: bool | None = None

    airport_restriction: bool | None = None

    reservation_present: bool | None = None

    reservation_type: str | None = None

    # ==========================================================
    # BUILDING
    # ==========================================================

    building_type: str | None = None

    building_use: str | None = None

    mixed_use: bool | None = None

    group_housing: bool | None = None

    redevelopment: bool | None = None

    rehabilitation: bool | None = None

    existing_building: bool = False

    building_height: float | None = None

    number_of_floors: int | None = None

    floor_height: float | None = None

    # ==========================================================
    # USER REQUIREMENTS
    # ==========================================================

    requested_units: int | None = None

    requested_1bhk_units: int | None = None

    requested_2bhk_units: int | None = None

    requested_3bhk_units: int | None = None

    requested_commercial_area: float | None = None

    requested_residential_area: float | None = None

    requested_height: float | None = None

    requested_floors: int | None = None

    requested_fsi: float | None = None

    # ==========================================================
    # DESIGN OBJECTIVE
    # ==========================================================

    maximize_fsi: bool = True

    maximize_parking: bool = True

    maximize_usable_area: bool = True

    optimize_daylight: bool = True

    optimize_ventilation: bool = True

    # ==========================================================
    # GEOMETRY / DERIVED FACTS
    # ==========================================================

    site_facts: dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================================================
    # ADDITIONAL FACTS
    # ==========================================================

    additional_facts: dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================================================
    # TO DICT
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:

        result = {
            "project_id": self.project_id,
            "project_type": self.project_type,
            "development_type": self.development_type,

            "plot_area": self.plot_area,
            "plot_number": self.plot_number,
            "boundary": self.boundary,
            "north_direction": self.north_direction,
            "plot_shape": self.plot_shape,

            "road_width": self.road_width,
            "road_widths": self.road_widths,
            "road_frontage_count":
                self.road_frontage_count,
            "road_locations":
                self.road_locations,
            "road_type": self.road_type,
            "road_name": self.road_name,
            "road_classification":
                self.road_classification,
            "access_available":
                self.access_available,

            "latitude": self.latitude,
            "longitude": self.longitude,
            "location": self.location,
            "village": self.village,
            "city": self.city,
            "district": self.district,
            "state": self.state,

            "planning_authority":
                self.planning_authority,
            "development_authority":
                self.development_authority,
            "municipality":
                self.municipality,

            "zone_type": self.zone_type,
            "land_use_zone":
                self.land_use_zone,
            "land_use_classification":
                self.land_use_classification,
            "congested_area":
                self.congested_area,

            "tod_zone": self.tod_zone,
            "heritage_zone":
                self.heritage_zone,
            "crz_zone": self.crz_zone,
            "eco_sensitive_zone":
                self.eco_sensitive_zone,
            "airport_restriction":
                self.airport_restriction,

            "reservation_present":
                self.reservation_present,
            "reservation_type":
                self.reservation_type,

            "building_type":
                self.building_type,
            "building_use":
                self.building_use,
            "mixed_use": self.mixed_use,
            "group_housing":
                self.group_housing,
            "redevelopment":
                self.redevelopment,
            "rehabilitation":
                self.rehabilitation,
            "existing_building":
                self.existing_building,

            "building_height":
                self.building_height,
            "number_of_floors":
                self.number_of_floors,
            "floor_height":
                self.floor_height,

            "requested_units":
                self.requested_units,
            "requested_1bhk_units":
                self.requested_1bhk_units,
            "requested_2bhk_units":
                self.requested_2bhk_units,
            "requested_3bhk_units":
                self.requested_3bhk_units,

            "requested_commercial_area":
                self.requested_commercial_area,
            "requested_residential_area":
                self.requested_residential_area,

            "requested_height":
                self.requested_height,
            "requested_floors":
                self.requested_floors,
            "requested_fsi":
                self.requested_fsi,

            "maximize_fsi":
                self.maximize_fsi,
            "maximize_parking":
                self.maximize_parking,
            "maximize_usable_area":
                self.maximize_usable_area,
            "optimize_daylight":
                self.optimize_daylight,
            "optimize_ventilation":
                self.optimize_ventilation,
        }

        result = {
            key: value
            for key, value in result.items()
            if value is not None
        }

        result.update(self.site_facts)
        result.update(self.additional_facts)

        return result

    # ==========================================================
    # CANONICAL PLANNING FACTS
    # ==========================================================

    def to_planning_facts(self) -> PlanningFacts:
        """
        Convert the broader PlanningFactContext into the
        canonical PlanningFacts model used by the regulatory
        rule engine.

        No regulatory inference or defaults are applied here.

        Unknown values remain None.
        """

        values = {
            "project_id": self.project_id,
            "project_type": self.project_type,
            "development_type": self.development_type,

            "location": self.location,
            "village": self.village,
            "city": self.city,
            "district": self.district,
            "state": self.state,

            "planning_authority":
                self.planning_authority,
            "development_authority":
                self.development_authority,
            "municipality":
                self.municipality,

            "zone_type": self.zone_type,
            "land_use_zone":
                self.land_use_zone,
            "land_use_classification":
                self.land_use_classification,

            "road_type": self.road_type,
            "road_name": self.road_name,
            "road_classification":
                self.road_classification,

            "tod_zone": self.tod_zone,
            "heritage_zone":
                self.heritage_zone,
            "crz_zone": self.crz_zone,
            "eco_sensitive_zone":
                self.eco_sensitive_zone,
            "airport_restriction":
                self.airport_restriction,

            "reservation_present":
                self.reservation_present,
            "reservation_type":
                self.reservation_type,

            "mixed_use": self.mixed_use,
            "group_housing":
                self.group_housing,
            "rehabilitation":
                self.rehabilitation,

            "requested_units":
                self.requested_units,
            "requested_1bhk_units":
                self.requested_1bhk_units,
            "requested_2bhk_units":
                self.requested_2bhk_units,
            "requested_3bhk_units":
                self.requested_3bhk_units,

            "requested_commercial_area":
                self.requested_commercial_area,
            "requested_residential_area":
                self.requested_residential_area,

            "requested_height":
                self.requested_height,
            "requested_floors":
                self.requested_floors,

            "latitude": self.latitude,
            "longitude": self.longitude,

            # Preserve existing specialized facts.
            **self.site_facts,
            **self.additional_facts,
        }

        # Remove unknown values. This is important because
        # missing facts must remain genuinely missing to the
        # tri-state rule engine.
        values = {
            key: value
            for key, value in values.items()
            if value is not None
        }

        facts =  PlanningFacts(
            project_id=self.project_id,
            project_type=self.project_type,
            development_type=self.development_type,

            plot_area=self.plot_area,
            plot_number=self.plot_number,

            boundary=self.boundary,
            north_direction=self.north_direction,
            plot_shape=self.plot_shape,

            road_width=self.road_width,
            road_widths=list(self.road_widths),
            road_frontage_count=self.road_frontage_count,
            road_locations=list(self.road_locations),

            road_type=self.road_type,
            road_name=self.road_name,
            road_classification=
                self.road_classification,
            access_available=
                self.access_available,

            latitude=self.latitude,
            longitude=self.longitude,
            location=self.location,
            village=self.village,
            city=self.city,
            district=self.district,
            state=self.state,
            location_type=None,

            planning_authority=
                self.planning_authority,
            development_authority=
                self.development_authority,
            municipality=self.municipality,

            zone=self.land_use_zone,
            zone_type=self.zone_type,
            land_use_zone=
                self.land_use_zone,
            land_use_classification=
                self.land_use_classification,
            congested_area=
                self.congested_area,

            tod_zone=self.tod_zone,
            heritage_zone=
                self.heritage_zone,
            crz_zone=self.crz_zone,
            eco_sensitive_zone=
                self.eco_sensitive_zone,
            airport_restriction=
                self.airport_restriction,

            reservation_present=
                self.reservation_present,
            reservation_type=
                self.reservation_type,

            building_type=
                self.building_type,
            building_use=
                self.building_use,
            building_height=
                self.building_height,
            number_of_floors=
                self.number_of_floors,
            floor_height=
                self.floor_height,

            mixed_use=self.mixed_use,
            group_housing=
                self.group_housing,
            redevelopment=bool(
                self.redevelopment
            ),
            rehabilitation=
                self.rehabilitation,
            existing_building=
                self.existing_building,

            requested_units=
                self.requested_units,
            requested_1bhk_units=
                self.requested_1bhk_units,
            requested_2bhk_units=
                self.requested_2bhk_units,
            requested_3bhk_units=
                self.requested_3bhk_units,

            requested_commercial_area=
                self.requested_commercial_area,
            requested_residential_area=
                self.requested_residential_area,

            requested_height=
                self.requested_height,
            requested_floors=
                self.requested_floors,

            requested_fsi=
                self.requested_fsi,

            maximize_fsi=
                self.maximize_fsi,
            maximize_parking=
                self.maximize_parking,
            maximize_usable_area=
                self.maximize_usable_area,
            optimize_daylight=
                self.optimize_daylight,
            optimize_ventilation=
                self.optimize_ventilation,

            values=values,
        )
        return facts.normalize()