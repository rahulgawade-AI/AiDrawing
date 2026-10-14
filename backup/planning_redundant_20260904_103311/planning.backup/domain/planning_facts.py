from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlanningFacts:
    """
    Canonical facts used to evaluate UDCPR rules.

    PlanningFacts is the regulatory input model.

    Facts may originate from:
        - Vision pipeline
        - GIS/site intelligence
        - User requirements
        - PlanningFactContext
        - Existing project/site data

    This class contains facts only.
    It does not evaluate rules or calculate constraints.
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

    survey_number: str | None = None

    cts_number: str | None = None

    boundary: Any | None = None

    north_direction: float | None = None

    plot_shape: str | None = None

    # ==========================================================
    # ROAD / ACCESS
    # ==========================================================

    road_width: float | None = None

    road_widths: list[float] = field(default_factory=list)

    road_frontage_count: int = 0

    road_locations: list[str] = field(default_factory=list)

    road_type: str | None = None

    road_name: str | None = None

    road_classification: str | None = None

    access_available: bool | None = None

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

    location_type: str | None = None

    # ==========================================================
    # PLANNING AUTHORITY
    # ==========================================================

    planning_authority: str | None = None

    development_authority: str | None = None

    municipality: str | None = None

    # ==========================================================
    # ZONING
    # ==========================================================

    zone: str | None = None

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

    building_height: float | None = None

    number_of_floors: int | None = None

    floor_height: float | None = None

    mixed_use: bool | None = None

    group_housing: bool | None = None

    redevelopment: bool = False

    rehabilitation: bool | None = None

    existing_building: bool = False

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
    # DESIGN OBJECTIVES
    # ==========================================================

    maximize_fsi: bool = True

    maximize_parking: bool = True

    maximize_usable_area: bool = True

    optimize_daylight: bool = True

    optimize_ventilation: bool = True

    # ==========================================================
    # ADDITIONAL / SPECIALIZED FACTS
    # ==========================================================

    values: dict[str, Any] = field(default_factory=dict)

    # ==========================================================
    # FACT LOOKUP
    # ==========================================================

    def get(self, field_name: str) -> Any:
        """
        Resolve a rule condition field to its canonical value.

        Supports both snake_case and common camelCase
        representations used by the UDCPR rule database.
        """

        aliases = {
            # --------------------------------------------------
            # Project
            # --------------------------------------------------

            "projectId": "project_id",
            "project_id": "project_id",

            "projectType": "project_type",
            "project_type": "project_type",

            "developmentType": "development_type",
            "development_type": "development_type",

            # --------------------------------------------------
            # Site
            # --------------------------------------------------

            "plotArea": "plot_area",
            "plot_area": "plot_area",

            "plotNumber": "plot_number",
            "plot_number": "plot_number",

            "surveyNumber": "survey_number",
            "survey_number": "survey_number",

            "ctsNumber": "cts_number",
            "cts_number": "cts_number",

            "northDirection": "north_direction",
            "north_direction": "north_direction",

            "plotShape": "plot_shape",
            "plot_shape": "plot_shape",

            # --------------------------------------------------
            # Road
            # --------------------------------------------------

            "roadWidth": "road_width",
            "road_width": "road_width",

            "roadWidths": "road_widths",
            "road_widths": "road_widths",

            "roadType": "road_type",
            "road_type": "road_type",

            "roadName": "road_name",
            "road_name": "road_name",

            "roadClassification": "road_classification",
            "road_classification": "road_classification",

            "roadFrontageCount": "road_frontage_count",
            "road_frontage_count": "road_frontage_count",

            "roadLocations": "road_locations",
            "road_locations": "road_locations",

            "accessAvailable": "access_available",
            "access_available": "access_available",

            # --------------------------------------------------
            # Location
            # --------------------------------------------------

            "latitude": "latitude",
            "longitude": "longitude",

            "location": "location",

            "village": "village",
            "city": "city",
            "district": "district",
            "state": "state",

            "locationType": "location_type",
            "location_type": "location_type",

            # --------------------------------------------------
            # Authority
            # --------------------------------------------------

            "planningAuthority": "planning_authority",
            "planning_authority": "planning_authority",

            "developmentAuthority": "development_authority",
            "development_authority": "development_authority",

            "municipality": "municipality",

            # --------------------------------------------------
            # Zoning
            # --------------------------------------------------

            "zone": "zone",

            "zoneType": "zone_type",
            "zone_type": "zone_type",

            "landUseZone": "land_use_zone",
            "land_use_zone": "land_use_zone",

            "landUseClassification": "land_use_classification",
            "land_use_classification": "land_use_classification",

            "congestedArea": "congested_area",
            "congested_area": "congested_area",

            # --------------------------------------------------
            # Special
            # --------------------------------------------------

            "todZone": "tod_zone",
            "tod_zone": "tod_zone",

            "heritageZone": "heritage_zone",
            "heritage_zone": "heritage_zone",

            "crzZone": "crz_zone",
            "crz_zone": "crz_zone",

            "ecoSensitiveZone": "eco_sensitive_zone",
            "eco_sensitive_zone": "eco_sensitive_zone",

            "airportRestriction": "airport_restriction",
            "airport_restriction": "airport_restriction",

            "reservationPresent": "reservation_present",
            "reservation_present": "reservation_present",

            "reservationType": "reservation_type",
            "reservation_type": "reservation_type",

            # --------------------------------------------------
            # Building
            # --------------------------------------------------

            "buildingType": "building_type",
            "building_type": "building_type",

            "buildingUse": "building_use",
            "building_use": "building_use",

            "buildingHeight": "building_height",
            "building_height": "building_height",

            "heightLimit": "building_height",

            "numberOfFloors": "number_of_floors",
            "number_of_floors": "number_of_floors",

            "floorHeight": "floor_height",
            "floor_height": "floor_height",

            "mixedUse": "mixed_use",
            "mixed_use": "mixed_use",

            "groupHousing": "group_housing",
            "group_housing": "group_housing",

            "redevelopment": "redevelopment",

            "rehabilitation": "rehabilitation",

            "existingBuilding": "existing_building",
            "existing_building": "existing_building",

            # --------------------------------------------------
            # Requirements
            # --------------------------------------------------

            "requestedUnits": "requested_units",
            "requested_units": "requested_units",

            "requested1BHKUnits": "requested_1bhk_units",
            "requested_1bhk_units": "requested_1bhk_units",

            "requested2BHKUnits": "requested_2bhk_units",
            "requested_2bhk_units": "requested_2bhk_units",

            "requested3BHKUnits": "requested_3bhk_units",
            "requested_3bhk_units": "requested_3bhk_units",

            "requestedCommercialArea":
                "requested_commercial_area",

            "requested_commercial_area":
                "requested_commercial_area",

            "requestedResidentialArea":
                "requested_residential_area",

            "requested_residential_area":
                "requested_residential_area",

            "requestedHeight": "requested_height",
            "requested_height": "requested_height",

            "requestedFloors": "requested_floors",
            "requested_floors": "requested_floors",

            "requestedFSI": "requested_fsi",
            "requested_fsi": "requested_fsi",
        }

        canonical = aliases.get(
            field_name,
            field_name,
        )

        if hasattr(self, canonical):
            return getattr(self, canonical)

        return self.values.get(canonical)

    # ==========================================================
    # NORMALIZATION
    # ==========================================================

    def normalize(self) -> "PlanningFacts":
        """
        Normalize common planning vocabulary into the canonical
        vocabulary used by the ingested UDCPR rules.

        This performs vocabulary normalization only.

        It does NOT infer:
            - zoning
            - location
            - authority
            - FSI
            - height
            - setbacks
            - parking
            - fire requirements
            - any other regulatory value
        """

        # ------------------------------------------------------
        # Building type
        # ------------------------------------------------------

        if self.building_type:
            value = self.building_type.strip()

            building_type_map = {
                "residential": "Residential building",
                "residential building":
                    "Residential building",
                "residential buildings":
                    "Residential Buildings",

                "mixed use":
                    "Mixed Use Developments",

                "mixed-use":
                    "Mixed Use Developments",

                "mixed use development":
                    "Mixed Use Developments",

                "commercial":
                    "Commercial",

                "commercial building":
                    "Commercial",

                "institutional":
                    "Institutional or Educational",

                "educational":
                    "Institutional or Educational",

                "assembly":
                    "Assembly",

                "special building":
                    "Special Building",

                "other":
                    "Other",

                "other building":
                    "other building",

                "individual residential building":
                    "individual residential building",

                "retirement home":
                    "Retirement Home",

                "senior citizen housing":
                    "Senior Citizen Housing",

                "residential hotel":
                    "Residential Hotel",

                "duplex tenement":
                    "Duplex Tenement",
            }

            normalized = building_type_map.get(
                value.lower()
            )

            if normalized:
                self.building_type = normalized

        # ------------------------------------------------------
        # Building use
        # ------------------------------------------------------

        if self.building_use:
            self.building_use = (
                self.building_use.strip().lower()
            )

        # ------------------------------------------------------
        # Zone
        # ------------------------------------------------------

        if self.zone:
            self.zone = self.zone.strip()

        if self.zone_type:
            self.zone_type = self.zone_type.strip()

        if self.land_use_zone:
            self.land_use_zone = (
                self.land_use_zone.strip()
            )

        if self.land_use_classification:
            self.land_use_classification = (
                self.land_use_classification.strip()
            )

        # ------------------------------------------------------
        # Road
        # ------------------------------------------------------

        if self.road_type:
            self.road_type = self.road_type.strip()

        if self.road_name:
            self.road_name = self.road_name.strip()

        if self.road_classification:
            self.road_classification = (
                self.road_classification.strip()
            )

        # ------------------------------------------------------
        # Location
        # ------------------------------------------------------

        if self.location:
            self.location = self.location.strip()

        if self.location_type:
            self.location_type = (
                self.location_type.strip()
            )

        # ------------------------------------------------------
        # Authorities
        # ------------------------------------------------------

        if self.planning_authority:
            self.planning_authority = (
                self.planning_authority.strip()
            )

        if self.development_authority:
            self.development_authority = (
                self.development_authority.strip()
            )

        if self.municipality:
            self.municipality = (
                self.municipality.strip()
            )

        return self

    # ==========================================================
    # SERIALIZATION
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Return all known planning facts.

        None values are intentionally omitted so that the
        RuleConditionEngine can distinguish missing facts
        from explicitly supplied values.
        """

        result = {
            # --------------------------------------------------
            # Project
            # --------------------------------------------------

            "project_id":
                self.project_id,

            "project_type":
                self.project_type,

            "development_type":
                self.development_type,

            # --------------------------------------------------
            # Site
            # --------------------------------------------------

            "plot_area":
                self.plot_area,

            "plot_number":
                self.plot_number,

            "survey_number":
                self.survey_number,

            "cts_number":
                self.cts_number,

            "boundary":
                self.boundary,

            "north_direction":
                self.north_direction,

            "plot_shape":
                self.plot_shape,

            # --------------------------------------------------
            # Road
            # --------------------------------------------------

            "road_width":
                self.road_width,

            "road_widths":
                self.road_widths,

            "road_frontage_count":
                self.road_frontage_count,

            "road_locations":
                self.road_locations,

            "road_type":
                self.road_type,

            "road_name":
                self.road_name,

            "road_classification":
                self.road_classification,

            "access_available":
                self.access_available,

            # --------------------------------------------------
            # Location
            # --------------------------------------------------

            "latitude":
                self.latitude,

            "longitude":
                self.longitude,

            "location":
                self.location,

            "village":
                self.village,

            "city":
                self.city,

            "district":
                self.district,

            "state":
                self.state,

            "location_type":
                self.location_type,

            # --------------------------------------------------
            # Authority
            # --------------------------------------------------

            "planning_authority":
                self.planning_authority,

            "development_authority":
                self.development_authority,

            "municipality":
                self.municipality,

            # --------------------------------------------------
            # Zoning
            # --------------------------------------------------

            "zone":
                self.zone,

            "zone_type":
                self.zone_type,

            "land_use_zone":
                self.land_use_zone,

            "land_use_classification":
                self.land_use_classification,

            "congested_area":
                self.congested_area,

            # --------------------------------------------------
            # Special zones
            # --------------------------------------------------

            "tod_zone":
                self.tod_zone,

            "heritage_zone":
                self.heritage_zone,

            "crz_zone":
                self.crz_zone,

            "eco_sensitive_zone":
                self.eco_sensitive_zone,

            "airport_restriction":
                self.airport_restriction,

            "reservation_present":
                self.reservation_present,

            "reservation_type":
                self.reservation_type,

            # --------------------------------------------------
            # Building
            # --------------------------------------------------

            "building_type":
                self.building_type,

            "building_use":
                self.building_use,

            "building_height":
                self.building_height,

            "number_of_floors":
                self.number_of_floors,

            "floor_height":
                self.floor_height,

            "mixed_use":
                self.mixed_use,

            "group_housing":
                self.group_housing,

            "redevelopment":
                self.redevelopment,

            "rehabilitation":
                self.rehabilitation,

            "existing_building":
                self.existing_building,

            # --------------------------------------------------
            # Requirements
            # --------------------------------------------------

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

            # --------------------------------------------------
            # Objectives
            # --------------------------------------------------

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

        # ------------------------------------------------------
        # Remove only None values.
        #
        # False and zero are valid facts and MUST be retained.
        # ------------------------------------------------------

        result = {
            key: value
            for key, value in result.items()
            if value is not None
        }

        # ------------------------------------------------------
        # Preserve specialized facts.
        #
        # These may include facts generated by:
        #   - Vision
        #   - GIS
        #   - Site analysis
        #   - Future engineering modules
        # ------------------------------------------------------

        result.update(self.values)

        return result