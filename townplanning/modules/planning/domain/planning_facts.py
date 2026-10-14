from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlanningFacts:
    """
    Canonical deterministic planning state for the UDCPR planning engine.

    PlanningFacts contains the canonical facts consumed by the rule engine.
    It may contain both source facts (user/survey/GIS/authority/image) and
    deterministic regulatory values resolved from the authoritative database.

    Regulatory fields in this class are STATE, not calculations performed by
    PlanningFacts itself. The deterministic rule engine is the only component
    allowed to populate them. No LLM is allowed to invent or calculate a
    regulatory value.

    Facts may originate from:
        - Vision pipeline
        - GIS/site intelligence
        - Survey / measurement sheet
        - Ownership / land records
        - User requirements
        - PlanningFactContext
        - Existing project/site data
        - Authority-provided information

    This class DOES NOT independently calculate or interpret regulations.
    Deterministic planning/rule services populate the regulatory state after
    resolving the applicable database rules and any dependent rules.

    Therefore the lifecycle is:
        source facts -> database rule resolution -> deterministic values
        -> PlanningFacts updated with the resolved values -> repeat dependent
        rules until stable -> ask the user only for genuinely missing inputs.

    IMPORTANT
    ---------
    A value being represented here does NOT mean that it is required
    for every project.

    Applicability is determined by:
        - project type
        - development type
        - land-use zone
        - building use
        - occupancy
        - height
        - plot size
        - road/access conditions
        - special restrictions
        - applicable UDCPR rules
    """

    # ==========================================================
    # PROJECT
    # ==========================================================

    project_id: str | None = None

    project_type: str | None = None

    development_type: str | None = None

    project_description: str | None = None

    proposal_stage: str | None = None

    # ==========================================================
    # SITE IDENTIFICATION
    # ==========================================================

    plot_number: str | None = None

    survey_number: str | None = None

    gat_number: str | None = None

    cts_number: str | None = None

    final_plot_number: str | None = None

    tp_scheme_number: str | None = None

    village: str | None = None

    taluka: str | None = None

    city: str | None = None

    district: str | None = None

    state: str | None = None

    location: str | None = None

    location_type: str | None = None

    latitude: float | None = None

    longitude: float | None = None

    # ==========================================================
    # PLOT / SITE GEOMETRY
    # ==========================================================

    plot_area: float | None = None

    plot_area_ownership_document: float | None = None

    plot_area_measurement_sheet: float | None = None

    plot_area_site_measurement: float | None = None

    plot_width: float | None = None

    plot_depth: float | None = None

    plot_shape: str | None = None

    plot_side_lengths: dict[str, float] = field(
        default_factory=dict
    )

    boundary: Any | None = None

    boundary_geometry: Any | None = None

    north_direction: float | None = None

    site_level: float | None = None

    average_site_level: float | None = None

    # ==========================================================
    # ROAD / FRONTAGE
    # ==========================================================

    road_width: float | None = None

    road_widths: list[float] = field(
        default_factory=list
    )

    road_frontage_count: int = 0

    road_frontages: list[dict[str, Any]] = field(
        default_factory=list
    )

    road_locations: list[str] = field(
        default_factory=list
    )

    road_type: str | None = None

    road_types: list[str] = field(
        default_factory=list
    )

    road_name: str | None = None

    road_names: list[str] = field(
        default_factory=list
    )

    road_classification: str | None = None

    road_classifications: list[str] = field(
        default_factory=list
    )

    road_reservation_width: float | None = None

    proposed_road_width: float | None = None

    line_of_street_present: bool | None = None

    # ==========================================================
    # ACCESS
    # ==========================================================

    access_available: bool | None = None

    access_width: float | None = None

    access_length: float | None = None

    access_location: str | None = None

    access_type: str | None = None

    access_from_public_road: bool | None = None

    dead_end_access: bool | None = None

    dead_end_access_length: float | None = None

    land_locked: bool | None = None

    point_access: bool | None = None

    internal_access_road: bool | None = None

    # ==========================================================
    # PLANNING AUTHORITY
    # ==========================================================

    planning_authority: str | None = None

    development_authority: str | None = None

    municipality: str | None = None

    municipal_corporation: str | None = None

    local_authority: str | None = None

    competent_authority: str | None = None

    # ==========================================================
    # PLANNING DOCUMENT / PLAN STATUS
    # ==========================================================

    development_plan_status: str | None = None

    development_plan_number: str | None = None

    regional_plan_status: str | None = None

    regional_plan_number: str | None = None

    development_plan_zone: str | None = None

    zoning_certificate_available: bool | None = None

    zoning_certificate_number: str | None = None

    zoning_certificate_date: str | None = None

    # ==========================================================
    # ZONING
    # ==========================================================

    zone: str | None = None

    zone_type: str | None = None

    land_use_zone: str | None = None

    land_use_classification: str | None = None

    proposed_land_use: str | None = None

    congested_area: bool | None = None

    # ==========================================================
    # SPECIAL ZONES / DEVELOPMENT CONDITIONS
    # ==========================================================

    tod_zone: bool | None = None

    heritage_zone: bool | None = None

    heritage_restriction: bool | None = None

    crz_zone: bool | None = None

    eco_sensitive_zone: bool | None = None

    forest_zone: bool | None = None

    agriculture_zone: bool | None = None

    tourism_zone: bool | None = None

    hill_station: bool | None = None

    gaothan_area: bool | None = None

    gaothan_distance: float | None = None

    # ==========================================================
    # RESERVATION
    # ==========================================================

    reservation_present: bool | None = None

    reservation_type: str | None = None

    reservation_number: str | None = None

    reservation_area: float | None = None

    reservation_handover_proposed: bool | None = None

    reservation_handover_area: float | None = None

    deemed_reservation: bool | None = None

    # ==========================================================
    # DP / RP ROAD / ROAD WIDENING
    # ==========================================================

    dp_road_present: bool | None = None

    dp_road_area: float | None = None

    road_widening: bool | None = None

    road_widening_area: float | None = None

    highway_widening: bool | None = None

    highway_widening_area: float | None = None

    service_road_present: bool | None = None

    service_road_area: float | None = None

    # ==========================================================
    # AREA STATEMENT INPUTS
    #
    # These correspond to the UDCPR area-statement structure.
    # ==========================================================

    total_area_under_development: float | None = None

    deduction_dp_road: float | None = None

    deduction_road_widening: float | None = None

    deduction_service_road: float | None = None

    deduction_highway_widening: float | None = None

    deduction_reservation: float | None = None

    balance_plot_area: float | None = None

    amenity_space_required: float | None = None

    amenity_space_proposed: float | None = None

    amenity_space_adjustment: float | None = None

    net_plot_area: float | None = None

    recreational_open_space_required: float | None = None

    recreational_open_space_proposed: float | None = None

    internal_road_area: float | None = None

    plotable_area: float | None = None

    pro_rata_fsi_factor: float | None = None

    inclusive_housing_required_area: float | None = None

    inclusive_housing_proposed_area: float | None = None

    # ==========================================================
    # OPEN SPACE
    # ==========================================================

    recreational_open_space_required_percent: float | None = None

    recreational_open_space_minimum_area: float | None = None

    recreational_open_space_on_podium: bool | None = None

    recreational_open_space_on_terrace: bool | None = None

    common_open_space_required: float | None = None

    common_open_space_proposed: float | None = None

    minimum_open_space_m2: float | None = None
    recreational_open_space_m2: float | None = None
    amenity_space_m2: float | None = None

    # ==========================================================
    # GROUP HOUSING / LAYOUT
    # ==========================================================

    group_housing: bool | None = None

    layout_development: bool | None = None

    subdivision: bool | None = None

    number_of_plots: int | None = None

    number_of_buildings: int | None = None

    number_of_wings: int | None = None

    internal_road_length: float | None = None

    internal_road_width: float | None = None

    internal_road_lengths: list[float] = field(
        default_factory=list
    )

    internal_road_widths: list[float] = field(
        default_factory=list
    )

    # ==========================================================
    # BUILDING
    # ==========================================================

    building_type: str | None = None

    building_use: str | None = None

    occupancy: str | None = None

    occupancy_type: str | None = None

    special_building: bool | None = None

    mixed_use: bool | None = None

    group_housing_building: bool | None = None

    # ==========================================================
    # BUILDING HEIGHT / FLOORS
    # ==========================================================

    # Observed/proposed building height. This may come from an existing
    # proposal/drawing or an explicit user requirement. It is NOT the
    # regulatory maximum height.
    building_height: float | None = None

    requested_height: float | None = None

    maximum_requested_height: float | None = None

    number_of_floors: int | None = None

    requested_floors: int | None = None

    floor_height: float | None = None

    # ----------------------------------------------------------
    # REGULATORY / DESIGN OUTPUTS
    #
    # These are populated AFTER deterministic UDCPR rule
    # resolution. They must never be supplied by the vision LLM
    # as regulatory facts.
    # ----------------------------------------------------------
    maximum_height_m: float | None = None
    maximum_storeys: int | None = None
    maximum_ground_coverage: float | None = None
    selected_floor_count: int | None = None

    # Authority/approval facts used to resolve height. For Pune,
    # UDCPR 6.10 delegates permissible height to Fire Department
    # approval, so a project-specific approved height may be needed.
    fire_approved_height_m: float | None = None
    height_approval_required: bool | None = None
    height_limit_basis: str | None = None

    # Authority approval / NOC facts. These are INPUTS when supplied by an
    # authority and are never inferred from city/zone names.
    fire_approval_status: str | None = None
    fire_approval_authority: str | None = None
    fire_approved_height_source: str | None = None
    airport_noc_required: bool | None = None
    airport_noc_available: bool | None = None
    airport_noc_number: str | None = None
    airport_clearance_height_m: float | None = None
    heritage_noc_required: bool | None = None
    heritage_noc_available: bool | None = None
    heritage_noc_number: str | None = None
    crz_clearance_required: bool | None = None
    crz_clearance_available: bool | None = None
    crz_clearance_number: str | None = None
    environmental_clearance_required: bool | None = None
    environmental_clearance_available: bool | None = None
    environmental_clearance_number: str | None = None
    forest_clearance_required: bool | None = None
    forest_clearance_available: bool | None = None
    forest_clearance_number: str | None = None
    defence_noc_required: bool | None = None
    defence_noc_available: bool | None = None
    defence_noc_number: str | None = None
    railway_noc_required: bool | None = None
    railway_noc_available: bool | None = None
    railway_noc_number: str | None = None
    water_authority_approval_required: bool | None = None
    water_authority_approval_available: bool | None = None
    sewer_authority_approval_required: bool | None = None
    sewer_authority_approval_available: bool | None = None

    floor_heights: list[float] = field(
        default_factory=list
    )

    ground_floor_height: float | None = None

    basement_count: int | None = None

    podium_count: int | None = None

    stilt_floor: bool | None = None

    parking_floor_count: int | None = None

    # ==========================================================
    # BUILDING FOOTPRINT / DIMENSIONS
    #
    # These may be populated by a design engine later.
    # ==========================================================

    requested_building_footprint: float | None = None

    building_footprint: float | None = None

    building_length: float | None = None

    building_width: float | None = None

    building_orientation: float | None = None

    built_up_area: float | None = None

    floor_plate_area: float | None = None

    total_floor_area: float | None = None

    # ==========================================================
    # SETBACK / MARGIN FACTS
    #
    # These should normally be outputs of the rule engine.
    # They are retained here so that calculated facts can be
    # passed downstream without creating another incompatible
    # context object.
    # ==========================================================

    front_setback: float | None = None

    rear_setback: float | None = None

    side_setback_left: float | None = None

    side_setback_right: float | None = None

    side_margin: float | None = None

    rear_margin: float | None = None

    front_margin: float | None = None

    building_separation: float | None = None

    distance_between_buildings: float | None = None

    # ==========================================================
    # FSI / DEVELOPMENT POTENTIAL
    #
    # Regulatory values should normally be populated by the
    # deterministic rule engine, not by the LLM.
    # ==========================================================

    requested_fsi: float | None = None

    basic_fsi: float | None = None

    premium_fsi: float | None = None

    tdr_fsi: float | None = None

    ancillary_fsi: float | None = None

    maximum_fsi: float | None = None

    permissible_fsi: float | None = None

    basic_fsi_area: float | None = None

    premium_fsi_area: float | None = None

    tdr_fsi_area: float | None = None

    ancillary_fsi_area: float | None = None

    permissible_built_up_area: float | None = None

    maximum_built_up_area: float | None = None

    # Deterministic constraint outputs used by downstream approval/design.
    incentive_fsi: float | None = None
    total_fsi: float | None = None

    # ==========================================================
    # EXISTING BUILDING / REDEVELOPMENT
    # ==========================================================

    existing_building: bool = False

    redevelopment: bool = False

    reconstruction: bool | None = None

    rehabilitation: bool | None = None

    existing_building_height: float | None = None

    existing_number_of_floors: int | None = None

    existing_built_up_area: float | None = None

    existing_authorised_built_up_area: float | None = None

    existing_authorised_fsi: float | None = None

    existing_carpet_area: float | None = None

    existing_parking_spaces: int | None = None

    existing_use: str | None = None

    existing_authorisation_status: str | None = None

    # ==========================================================
    # RESIDENTIAL PROGRAM
    # ==========================================================

    requested_units: int | None = None

    requested_1bhk_units: int | None = None

    requested_2bhk_units: int | None = None

    requested_3bhk_units: int | None = None

    requested_4bhk_units: int | None = None

    requested_other_units: int | None = None

    requested_unit_mix: list[dict[str, Any]] | None = None

    requested_residential_area: float | None = None

    requested_commercial_area: float | None = None

    requested_institutional_area: float | None = None

    requested_amenity_area: float | None = None

    requested_common_area: float | None = None

    # ==========================================================
    # RESIDENTIAL TENEMENT DATA
    #
    # Needed because UDCPR parking provisions distinguish
    # tenement categories by carpet area.
    # ==========================================================

    tenement_count: int | None = None

    tenement_carpet_areas: dict[str, Any] = field(
        default_factory=dict
    )

    tenement_area_categories: list[dict[str, Any]] = field(
        default_factory=list
    )

    # ==========================================================
    # COMMERCIAL / OTHER USE PROGRAM
    # ==========================================================

    commercial_floor_area: float | None = None

    retail_area: float | None = None

    office_area: float | None = None

    institutional_area: float | None = None

    educational_area: float | None = None

    hospital_area: float | None = None

    assembly_area: float | None = None

    hotel_area: float | None = None

    industrial_area: float | None = None

    # ==========================================================
    # PARKING INPUTS
    # ==========================================================

    parking_mode: str | None = None

    parking_requirement_known: bool | None = None

    requested_car_parking_spaces: int | None = None

    requested_two_wheeler_spaces: int | None = None

    requested_visitor_parking_spaces: int | None = None

    existing_car_parking_spaces: int | None = None

    existing_two_wheeler_spaces: int | None = None

    parking_area: float | None = None

    parking_floor_area: float | None = None

    parking_drive_width: float | None = None

    parking_aisle_width: float | None = None

    parking_ramp_width: float | None = None

    parking_ramp_slope: float | None = None

    # Deterministic parking requirements resolved from applicable rules.
    car_parking_required: float | None = None
    two_wheeler_parking_required: float | None = None
    visitor_parking_required: float | None = None
    parking_area_required_m2: float | None = None

    # ==========================================================
    # FIRE / LIFE SAFETY INPUTS
    # ==========================================================

    fire_noc_required: bool | None = None

    fire_noc_available: bool | None = None

    fire_noc_number: str | None = None

    sprinkler_system: bool | None = None

    fire_fighting_system: bool | None = None

    fire_command_center: bool | None = None

    fire_access_available: bool | None = None

    fire_tender_movement_available: bool | None = None

    fire_tender_access_width: float | None = None

    fire_tender_access_distance: float | None = None

    # Deterministic fire/life-safety requirements.
    fire_access_required: bool | None = None
    fire_lift_required: bool | None = None
    fire_staircase_required: bool | None = None
    minimum_exit_count: int | None = None
    minimum_exit_width_m: float | None = None

    # ==========================================================
    # FLOOR / OCCUPANT DATA
    # ==========================================================

    floor_areas: list[float] = field(
        default_factory=list
    )

    floor_populations: dict[str, int] = field(
        default_factory=dict
    )

    proposed_floor_population: dict[str, int] = field(
        default_factory=dict
    )

    occupant_load: dict[str, float] = field(
        default_factory=dict
    )

    total_occupant_load: float | None = None

    # ==========================================================
    # STAIRS / EXITS
    # ==========================================================

    staircase_count: int | None = None

    staircase_width: float | None = None

    staircase_widths: list[float] = field(
        default_factory=list
    )

    staircase_type: str | None = None

    exit_count: int | None = None

    exit_width: float | None = None

    corridor_width: float | None = None

    maximum_travel_distance: float | None = None

    travel_distance: float | None = None

    horizontal_exit_required: bool | None = None

    refuge_area_required: float | None = None

    refuge_area_proposed: float | None = None

    # Additional deterministic circulation/accessibility requirements.
    staircase_width_m: float | None = None
    corridor_width_m: float | None = None
    accessible_entrance_required: bool | None = None
    ramp_required: bool | None = None
    ramp_width_m: float | None = None
    ramp_gradient: float | None = None

    # ==========================================================
    # LIFT INPUTS / DESIGN OUTPUTS
    # ==========================================================

    lift_count: int | None = None

    passenger_lift_count: int | None = None

    fire_lift_count: int | None = None

    lift_required: bool | None = None

    lift_capacity: float | None = None

    lift_population: int | None = None

    lift_machine_room_required: bool | None = None

    # ==========================================================
    # BUILDING PARTS
    # ==========================================================

    room_areas: list[float] = field(
        default_factory=list
    )

    room_depths: list[float] = field(
        default_factory=list
    )

    habitable_room_count: int | None = None

    bedroom_count: int | None = None

    living_room_count: int | None = None

    kitchen_count: int | None = None

    bathroom_count: int | None = None

    water_closet_count: int | None = None

    balcony_count: int | None = None

    balcony_area: float | None = None

    terrace_area: float | None = None

    lobby_area: float | None = None

    corridor_area: float | None = None

    staircase_area: float | None = None

    lift_lobby_area: float | None = None

    lift_core_area: float | None = None

    # ==========================================================
    # LIGHT / VENTILATION
    # ==========================================================

    natural_light_available: bool | None = None

    natural_ventilation_available: bool | None = None

    room_opening_areas: dict[str, float] = field(
        default_factory=dict
    )

    room_ventilation_areas: dict[str, float] = field(
        default_factory=dict
    )

    ventilation_shaft_count: int | None = None

    ventilation_shaft_area: float | None = None

    duct_count: int | None = None

    duct_area: float | None = None

    # ==========================================================
    # SANITATION / SERVICES
    # ==========================================================

    water_supply_available: bool | None = None

    water_supply_source: str | None = None

    water_storage_required: bool | None = None

    water_storage_capacity: float | None = None

    sewerage_available: bool | None = None

    sewerage_connection_available: bool | None = None

    septic_tank_required: bool | None = None

    drainage_available: bool | None = None

    rainwater_drainage_available: bool | None = None

    storm_water_management: bool | None = None

    # ==========================================================
    # ELECTRICAL / UTILITY
    # ==========================================================

    electrical_connection_available: bool | None = None

    electrical_substation_required: bool | None = None

    electrical_substation_area: float | None = None

    transformer_required: bool | None = None

    transformer_capacity: float | None = None

    generator_required: bool | None = None

    generator_area: float | None = None

    # ==========================================================
    # SPECIAL RESTRICTIONS
    # ==========================================================

    airport_restriction: bool | None = None

    site_elevation: float | None = None

    cczm_permissible_elevation: float | None = None

    airport_height_limit: float | None = None

    railway_proximity: bool | None = None

    railway_distance: float | None = None

    natural_lake_proximity: bool | None = None

    natural_lake_distance: float | None = None

    flood_line_status: str | None = None

    blue_flood_line_distance: float | None = None

    red_flood_line_distance: float | None = None

    nallah_or_watercourse: bool | None = None

    nallah_distance: float | None = None

    river_proximity: bool | None = None

    river_distance: float | None = None

    heritage_restriction: bool | None = None

    heritage_structure_present: bool | None = None

    heritage_buffer_distance: float | None = None

    defence_restriction: bool | None = None

    defence_distance: float | None = None

    # ==========================================================
    # ENVIRONMENT / SITE CONDITIONS
    # ==========================================================

    tree_present: bool | None = None

    protected_tree_present: bool | None = None

    tree_count: int | None = None

    slope_percent: float | None = None

    steep_slope: bool | None = None

    soil_condition: str | None = None

    geotechnical_report_available: bool | None = None

    # ==========================================================
    # USER DESIGN OBJECTIVES
    # ==========================================================

    maximize_fsi: bool = True

    maximize_parking: bool = True

    maximize_usable_area: bool = True

    optimize_daylight: bool = True

    optimize_ventilation: bool = True

    optimize_orientation: bool = True

    minimize_common_area: bool = False

    minimize_construction_area: bool = False

    maximize_open_space: bool = False

    maximize_green_area: bool = False

    minimize_building_height: bool = False

    # ==========================================================
    # SPECIAL USER CONSTRAINTS
    # ==========================================================

    mandatory_ground_floor_use: str | None = None

    mandatory_top_floor_use: str | None = None

    minimum_unit_area: float | None = None

    maximum_unit_area: float | None = None

    preferred_unit_area: float | None = None

    preferred_floor_plate_area: float | None = None

    preferred_building_orientation: float | None = None

    preferred_number_of_floors: int | None = None

    preferred_parking_mode: str | None = None

    # ==========================================================
    # DETERMINISTIC REGULATORY RESOLUTION STATE
    #
    # These fields are machine-readable state, not regulatory calculations.
    # The rule engine fills them while resolving the database rule graph.
    # ==========================================================

    regulatory_resolution_status: str = "not_started"
    regulatory_resolution_pass: int = 0
    regulatory_missing_inputs: list[str] = field(default_factory=list)
    regulatory_user_questions: list[dict[str, Any]] = field(default_factory=list)
    regulatory_required_approvals: list[dict[str, Any]] = field(default_factory=list)
    regulatory_pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    regulatory_dependencies: list[dict[str, Any]] = field(default_factory=list)
    regulatory_trace: list[dict[str, Any]] = field(default_factory=list)
    regulatory_values: dict[str, Any] = field(default_factory=dict)
    regulatory_errors: list[dict[str, Any]] = field(default_factory=list)

    # ==========================================================
    # ADDITIONAL / SPECIALIZED FACTS
    #
    # Vision, GIS, CAD, survey and future engineering modules
    # may put additional canonical facts here.
    # ==========================================================

    values: dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================================================
    # FACT PROVENANCE / CONFIDENCE
    # ==========================================================

    fact_sources: dict[str, str] = field(
        default_factory=dict
    )

    fact_confidence: dict[str, float] = field(
        default_factory=dict
    )

    fact_evidence: dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================================================
    # FACT LOOKUP
    # ==========================================================

    def get(
        self,
        field_name: str,
    ) -> Any:
        """
        Resolve a planning-rule condition field.

        Supports:
            - canonical snake_case
            - common camelCase
            - legacy field names
            - specialized values

        This method performs lookup only.

        It does NOT infer regulatory values.
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

            "projectDescription":
                "project_description",

            "proposalStage":
                "proposal_stage",

            # --------------------------------------------------
            # Site
            # --------------------------------------------------

            "plotArea": "plot_area",
            "plot_area": "plot_area",

            "plotNumber": "plot_number",
            "plot_number": "plot_number",

            "surveyNumber": "survey_number",
            "survey_number": "survey_number",

            "gatNumber": "gat_number",
            "gat_number": "gat_number",

            "ctsNumber": "cts_number",
            "cts_number": "cts_number",

            "finalPlotNumber":
                "final_plot_number",

            "tpSchemeNumber":
                "tp_scheme_number",

            "plotWidth": "plot_width",
            "plot_width": "plot_width",

            "plotDepth": "plot_depth",
            "plot_depth": "plot_depth",

            "plotShape": "plot_shape",
            "plot_shape": "plot_shape",

            "plotSideLengths":
                "plot_side_lengths",

            "boundary": "boundary",

            "northDirection":
                "north_direction",

            "north_direction":
                "north_direction",

            "siteLevel":
                "site_level",

            "averageSiteLevel":
                "average_site_level",

            # --------------------------------------------------
            # Area statement
            # --------------------------------------------------

            "plotAreaOwnershipDocument":
                "plot_area_ownership_document",

            "plotAreaMeasurementSheet":
                "plot_area_measurement_sheet",

            "plotAreaSiteMeasurement":
                "plot_area_site_measurement",

            "totalAreaUnderDevelopment":
                "total_area_under_development",

            "balancePlotArea":
                "balance_plot_area",

            "amenitySpaceRequired":
                "amenity_space_required",

            "amenitySpaceProposed":
                "amenity_space_proposed",

            "amenitySpaceAdjustment":
                "amenity_space_adjustment",

            "netPlotArea":
                "net_plot_area",

            "recreationalOpenSpaceRequired":
                "recreational_open_space_required",

            "recreationalOpenSpaceProposed":
                "recreational_open_space_proposed",

            "internalRoadArea":
                "internal_road_area",

            "plotableArea":
                "plotable_area",

            "proRataFsiFactor":
                "pro_rata_fsi_factor",

            "inclusiveHousingRequiredArea":
                "inclusive_housing_required_area",

            "inclusiveHousingProposedArea":
                "inclusive_housing_proposed_area",

            # --------------------------------------------------
            # Road
            # --------------------------------------------------

            "roadWidth": "road_width",
            "road_width": "road_width",

            "roadWidths": "road_widths",
            "road_widths": "road_widths",

            "roadFrontageCount":
                "road_frontage_count",

            "road_frontages":
                "road_frontages",

            "roadFrontages":
                "road_frontages",

            "roadLocations":
                "road_locations",

            "road_locations":
                "road_locations",

            "roadType":
                "road_type",

            "road_type":
                "road_type",

            "roadName":
                "road_name",

            "road_name":
                "road_name",

            "roadClassification":
                "road_classification",

            "road_classification":
                "road_classification",

            "roadReservationWidth":
                "road_reservation_width",

            "proposedRoadWidth":
                "proposed_road_width",

            # --------------------------------------------------
            # Access
            # --------------------------------------------------

            "accessAvailable":
                "access_available",

            "access_available":
                "access_available",

            "accessWidth":
                "access_width",

            "accessLength":
                "access_length",

            "accessLocation":
                "access_location",

            "accessType":
                "access_type",

            "accessFromPublicRoad":
                "access_from_public_road",

            "deadEndAccess":
                "dead_end_access",

            "deadEndAccessLength":
                "dead_end_access_length",

            "landLocked":
                "land_locked",

            "pointAccess":
                "point_access",

            # --------------------------------------------------
            # Location
            # --------------------------------------------------

            "latitude":
                "latitude",

            "longitude":
                "longitude",

            "location":
                "location",

            "village":
                "village",

            "taluka":
                "taluka",

            "city":
                "city",

            "district":
                "district",

            "state":
                "state",

            "locationType":
                "location_type",

            "location_type":
                "location_type",

            # --------------------------------------------------
            # Authority
            # --------------------------------------------------

            "planningAuthority":
                "planning_authority",

            "planning_authority":
                "planning_authority",

            "developmentAuthority":
                "development_authority",

            "development_authority":
                "development_authority",

            "municipality":
                "municipality",

            "municipalCorporation":
                "municipal_corporation",

            "localAuthority":
                "local_authority",

            "competentAuthority":
                "competent_authority",

            # --------------------------------------------------
            # Planning documents
            # --------------------------------------------------

            "developmentPlanStatus":
                "development_plan_status",

            "developmentPlanNumber":
                "development_plan_number",

            "regionalPlanStatus":
                "regional_plan_status",

            "regionalPlanNumber":
                "regional_plan_number",

            "developmentPlanZone":
                "development_plan_zone",

            "zoningCertificateAvailable":
                "zoning_certificate_available",

            "zoningCertificateNumber":
                "zoning_certificate_number",

            # --------------------------------------------------
            # Zoning
            # --------------------------------------------------

            "zone":
                "zone",

            "zoneType":
                "zone_type",

            "zone_type":
                "zone_type",

            "landUseZone":
                "land_use_zone",

            "land_use_zone":
                "land_use_zone",

            "landUseClassification":
                "land_use_classification",

            "land_use_classification":
                "land_use_classification",

            "proposedLandUse":
                "proposed_land_use",

            "congestedArea":
                "congested_area",

            "congested_area":
                "congested_area",

            # --------------------------------------------------
            # Special zones
            # --------------------------------------------------

            "todZone":
                "tod_zone",

            "heritageZone":
                "heritage_zone",

            "heritageRestriction":
                "heritage_restriction",

            "crzZone":
                "crz_zone",

            "ecoSensitiveZone":
                "eco_sensitive_zone",

            "forestZone":
                "forest_zone",

            "agricultureZone":
                "agriculture_zone",

            "tourismZone":
                "tourism_zone",

            "hillStation":
                "hill_station",

            "gaothanArea":
                "gaothan_area",

            # --------------------------------------------------
            # Reservation
            # --------------------------------------------------

            "reservationPresent":
                "reservation_present",

            "reservationType":
                "reservation_type",

            "reservationNumber":
                "reservation_number",

            "reservationArea":
                "reservation_area",

            "deemedReservation":
                "deemed_reservation",

            # --------------------------------------------------
            # Road widening
            # --------------------------------------------------

            "dpRoadPresent":
                "dp_road_present",

            "dpRoadArea":
                "dp_road_area",

            "roadWidening":
                "road_widening",

            "roadWideningArea":
                "road_widening_area",

            "highwayWidening":
                "highway_widening",

            "highwayWideningArea":
                "highway_widening_area",

            "serviceRoadPresent":
                "service_road_present",

            "serviceRoadArea":
                "service_road_area",

            # --------------------------------------------------
            # Building
            # --------------------------------------------------

            "buildingType":
                "building_type",

            "building_type":
                "building_type",

            "buildingUse":
                "building_use",

            "building_use":
                "building_use",

            "occupancy":
                "occupancy",

            "occupancyType":
                "occupancy_type",

            "specialBuilding":
                "special_building",

            "buildingHeight":
                "building_height",

            "building_height":
                "building_height",

            "heightLimit":
                "building_height",

            "numberOfFloors":
                "number_of_floors",

            "number_of_floors":
                "number_of_floors",

            "floorHeight":
                "floor_height",

            "floor_height":
                "floor_height",

            "mixedUse":
                "mixed_use",

            "groupHousing":
                "group_housing",

            "groupHousingBuilding":
                "group_housing_building",

            "redevelopment":
                "redevelopment",

            "reconstruction":
                "reconstruction",

            "rehabilitation":
                "rehabilitation",

            "existingBuilding":
                "existing_building",

            # --------------------------------------------------
            # User requirements
            # --------------------------------------------------

            "requestedUnits":
                "requested_units",

            "requested_units":
                "requested_units",

            "requested1BHKUnits":
                "requested_1bhk_units",

            "requested_1bhk_units":
                "requested_1bhk_units",

            "requested2BHKUnits":
                "requested_2bhk_units",

            "requested_2bhk_units":
                "requested_2bhk_units",

            "requested3BHKUnits":
                "requested_3bhk_units",

            "requested_3bhk_units":
                "requested_3bhk_units",

            "requested4BHKUnits":
                "requested_4bhk_units",

            "requested_4bhk_units":
                "requested_4bhk_units",

            "requestedUnitMix":
                "requested_unit_mix",

            "requested_unit_mix":
                "requested_unit_mix",

            "requestedCommercialArea":
                "requested_commercial_area",

            "requested_commercial_area":
                "requested_commercial_area",

            "requestedResidentialArea":
                "requested_residential_area",

            "requested_residential_area":
                "requested_residential_area",

            "requestedHeight":
                "requested_height",

            "requested_height":
                "requested_height",

            "requestedFloors":
                "requested_floors",

            "requested_floors":
                "requested_floors",

            "requestedFSI":
                "requested_fsi",

            "requested_fsi":
                "requested_fsi",

            # --------------------------------------------------
            # Parking
            # --------------------------------------------------

            "parkingMode":
                "parking_mode",

            "requestedCarParkingSpaces":
                "requested_car_parking_spaces",

            "requestedTwoWheelerSpaces":
                "requested_two_wheeler_spaces",

            "requestedVisitorParkingSpaces":
                "requested_visitor_parking_spaces",

            "tenementCarpetAreas":
                "tenement_carpet_areas",

            "existingParkingSpaces":
                "existing_parking_spaces",

            "parkingDriveWidth":
                "parking_drive_width",

            "parkingAisleWidth":
                "parking_aisle_width",

            "parkingRampWidth":
                "parking_ramp_width",

            "parkingRampSlope":
                "parking_ramp_slope",

            # --------------------------------------------------
            # Fire
            # --------------------------------------------------

            "fireNocRequired":
                "fire_noc_required",

            "fireNocAvailable":
                "fire_noc_available",

            "sprinklerSystem":
                "sprinkler_system",

            "fireFightingSystem":
                "fire_fighting_system",

            "fireAccessAvailable":
                "fire_access_available",

            "fireTenderMovementAvailable":
                "fire_tender_movement_available",

            # --------------------------------------------------
            # Floor / occupant
            # --------------------------------------------------

            "floorAreas":
                "floor_areas",

            "floorPopulations":
                "floor_populations",

            "proposedFloorPopulation":
                "proposed_floor_population",

            "occupantLoad":
                "occupant_load",

            "totalOccupantLoad":
                "total_occupant_load",

            # --------------------------------------------------
            # Stairs / exits
            # --------------------------------------------------

            "staircaseCount":
                "staircase_count",

            "staircaseWidth":
                "staircase_width",

            "staircaseWidths":
                "staircase_widths",

            "exitCount":
                "exit_count",

            "exitWidth":
                "exit_width",

            "corridorWidth":
                "corridor_width",

            "travelDistance":
                "travel_distance",

            "maximumTravelDistance":
                "maximum_travel_distance",

            "refugeAreaRequired":
                "refuge_area_required",

            "refugeAreaProposed":
                "refuge_area_proposed",

            # --------------------------------------------------
            # Lifts
            # --------------------------------------------------

            "liftCount":
                "lift_count",

            "passengerLiftCount":
                "passenger_lift_count",

            "fireLiftCount":
                "fire_lift_count",

            "liftRequired":
                "lift_required",

            "liftCapacity":
                "lift_capacity",

            # --------------------------------------------------
            # Special restrictions
            # --------------------------------------------------

            "airportRestriction":
                "airport_restriction",

            "siteElevation":
                "site_elevation",

            "cczmPermissibleElevation":
                "cczm_permissible_elevation",

            "airportHeightLimit":
                "airport_height_limit",

            "railwayProximity":
                "railway_proximity",

            "railwayDistance":
                "railway_distance",

            "naturalLakeProximity":
                "natural_lake_proximity",

            "naturalLakeDistance":
                "natural_lake_distance",

            "floodLineStatus":
                "flood_line_status",

            "blueFloodLineDistance":
                "blue_flood_line_distance",

            "redFloodLineDistance":
                "red_flood_line_distance",

            "nallahOrWatercourse":
                "nallah_or_watercourse",

            "nallahDistance":
                "nallah_distance",

            "heritageRestriction":
                "heritage_restriction",

            "defenceRestriction":
                "defence_restriction",

            # --------------------------------------------------
            # Services
            # --------------------------------------------------

            "waterSupplyAvailable":
                "water_supply_available",

            "waterSupplySource":
                "water_supply_source",

            "sewerageAvailable":
                "sewerage_available",

            "sewerageConnectionAvailable":
                "sewerage_connection_available",

            "septicTankRequired":
                "septic_tank_required",

            # --------------------------------------------------
            # Electrical
            # --------------------------------------------------

            "electricalSubstationRequired":
                "electrical_substation_required",

            "electricalSubstationArea":
                "electrical_substation_area",

            # --------------------------------------------------
            # Objectives
            # --------------------------------------------------

            "maximizeFSI":
                "maximize_fsi",

            "maximizeParking":
                "maximize_parking",

            "maximizeUsableArea":
                "maximize_usable_area",

            "optimizeDaylight":
                "optimize_daylight",

            "optimizeVentilation":
                "optimize_ventilation",
        }

        canonical = aliases.get(
            field_name,
            field_name,
        )

        if hasattr(
            self,
            canonical,
        ):
            return getattr(
                self,
                canonical,
            )

        return self.values.get(
            canonical
        )

    # ==========================================================
    # NORMALIZATION
    # ==========================================================

    def normalize(
        self,
    ) -> "PlanningFacts":
        """
        Normalize vocabulary only.

        This method MUST NOT infer regulatory values.

        It does NOT calculate:
            - FSI
            - setbacks
            - parking
            - height
            - fire requirements
            - lifts
            - stairs
            - open space
        """

        # ------------------------------------------------------
        # Project
        # ------------------------------------------------------

        if self.project_type:
            self.project_type = (
                self.project_type.strip()
            )

        if self.development_type:
            self.development_type = (
                self.development_type.strip()
            )

        # ------------------------------------------------------
        # Building type
        # ------------------------------------------------------

        if self.building_type:

            value = (
                self.building_type
                .strip()
            )

            building_type_map = {

                "residential":
                    "Residential building",

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

                "retirement home":
                    "Retirement Home",

                "senior citizen housing":
                    "Senior Citizen Housing",

                "residential hotel":
                    "Residential Hotel",

                "duplex tenement":
                    "Duplex Tenement",
            }

            normalized = (
                building_type_map.get(
                    value.lower()
                )
            )

            if normalized:
                self.building_type = (
                    normalized
                )

        # ------------------------------------------------------
        # Building use
        # ------------------------------------------------------

        if self.building_use:

            self.building_use = (
                self.building_use
                .strip()
                .lower()
            )

        # ------------------------------------------------------
        # Occupancy
        # ------------------------------------------------------

        if self.occupancy:

            self.occupancy = (
                self.occupancy
                .strip()
                .lower()
            )

        if self.occupancy_type:

            self.occupancy_type = (
                self.occupancy_type
                .strip()
                .lower()
            )

        # ------------------------------------------------------
        # Zone
        # ------------------------------------------------------

        if self.zone:
            self.zone = (
                self.zone.strip()
            )

        if self.zone_type:
            self.zone_type = (
                self.zone_type.strip()
            )

        if self.land_use_zone:
            self.land_use_zone = (
                self.land_use_zone
                .strip()
            )

        if self.land_use_classification:
            self.land_use_classification = (
                self.land_use_classification
                .strip()
            )

        # ------------------------------------------------------
        # Road
        # ------------------------------------------------------

        if self.road_type:

            self.road_type = (
                self.road_type.strip()
            )

        if self.road_name:

            self.road_name = (
                self.road_name.strip()
            )

        if self.road_classification:

            self.road_classification = (
                self.road_classification
                .strip()
            )

        # ------------------------------------------------------
        # Location
        # ------------------------------------------------------

        if self.location:

            self.location = (
                self.location.strip()
            )

        if self.location_type:

            self.location_type = (
                self.location_type
                .strip()
            )

        if self.village:

            self.village = (
                self.village.strip()
            )

        if self.city:

            self.city = (
                self.city.strip()
            )

        if self.district:

            self.district = (
                self.district.strip()
            )

        if self.state:

            self.state = (
                self.state.strip()
            )

        # ------------------------------------------------------
        # Authorities
        # ------------------------------------------------------

        if self.planning_authority:

            self.planning_authority = (
                self.planning_authority
                .strip()
            )

        if self.development_authority:

            self.development_authority = (
                self.development_authority
                .strip()
            )

        if self.municipality:

            self.municipality = (
                self.municipality.strip()
            )

        # ------------------------------------------------------
        # Normalize requested unit mix
        # ------------------------------------------------------

        if self.requested_unit_mix is None:

            self.requested_unit_mix = []

        # ------------------------------------------------------
        # Normalize road widths
        # ------------------------------------------------------

        normalized_widths = []

        for value in (
            self.road_widths or []
        ):

            try:
                normalized_widths.append(
                    float(value)
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

        self.road_widths = (
            normalized_widths
        )

        # ------------------------------------------------------
        # Keep single-road compatibility
        #
        # Do not select max road width when multiple roads exist.
        # ------------------------------------------------------

        if (
            len(self.road_widths)
            == 1
        ):

            self.road_width = (
                self.road_widths[0]
            )

        # ------------------------------------------------------
        # Normalize frontage count
        # ------------------------------------------------------

        if (
            self.road_frontages
            and self.road_frontage_count
            == 0
        ):

            self.road_frontage_count = (
                len(self.road_frontages)
            )

        # ------------------------------------------------------
        # Normalize floor heights
        # ------------------------------------------------------

        normalized_floor_heights = []

        for value in (
            self.floor_heights or []
        ):

            try:
                normalized_floor_heights.append(
                    float(value)
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

        self.floor_heights = (
            normalized_floor_heights
        )

        # ------------------------------------------------------
        # Normalize numerical values that may arrive as strings
        # ------------------------------------------------------

        numeric_fields = (

            "plot_area",

            "plot_width",

            "plot_depth",

            "requested_height",

            "requested_floors",

            "requested_units",

            "requested_fsi",

            "road_width",

            "access_width",

            "access_length",

            "building_height",

            "number_of_floors",

            "floor_height",

            "maximum_height_m",

            "maximum_storeys",

            "maximum_ground_coverage",

            "selected_floor_count",

            "fire_approved_height_m",
            "airport_clearance_height_m",

            "net_plot_area",

            "basic_fsi",

            "premium_fsi",

            "tdr_fsi",

            "ancillary_fsi",

            "maximum_fsi",

            "permissible_fsi",
            "incentive_fsi",
            "total_fsi",
            "maximum_ground_coverage",
            "car_parking_required",
            "two_wheeler_parking_required",
            "visitor_parking_required",
            "parking_area_required_m2",
            "minimum_exit_count",
            "minimum_exit_width_m",
            "staircase_width_m",
            "corridor_width_m",
            "ramp_width_m",
            "minimum_open_space_m2",
            "recreational_open_space_m2",
            "amenity_space_m2",
        )

        for field_name in numeric_fields:

            value = getattr(
                self,
                field_name,
                None,
            )

            if value is None:
                continue

            try:

                setattr(
                    self,
                    field_name,
                    float(value),
                )

            except (
                TypeError,
                ValueError,
            ):

                pass

        return self

    # ==========================================================
    # DETERMINISTIC REGULATORY RESOLUTION HELPERS
    # ==========================================================

    @classmethod
    def regulatory_value_fields(cls) -> set[str]:
        """Fields that may be populated by deterministic rule resolution."""
        return {
            name for name in cls.__dataclass_fields__
            if name in {
                "basic_fsi", "premium_fsi", "tdr_fsi", "incentive_fsi",
                "maximum_fsi", "permissible_fsi", "total_fsi",
                "basic_fsi_area", "premium_fsi_area", "tdr_fsi_area",
                "ancillary_fsi_area", "permissible_built_up_area",
                "maximum_built_up_area", "maximum_ground_coverage",
                "front_setback", "rear_setback", "side_setback",
                "side_setback_left", "side_setback_right", "side_rear_margins",
                "building_separation", "maximum_height_m", "maximum_storeys",
                "car_parking_required", "two_wheeler_parking_required",
                "visitor_parking_required", "parking_area_required_m2",
                "fire_access_required", "fire_lift_required",
                "fire_staircase_required", "minimum_exit_count",
                "minimum_exit_width_m", "staircase_count", "staircase_width_m",
                "corridor_width_m", "lift_required", "lift_count",
                "fire_lift_count", "accessible_entrance_required",
                "ramp_required", "ramp_width_m", "ramp_gradient",
                "minimum_open_space_m2", "recreational_open_space_m2",
                "amenity_space_m2", "refuge_area_required",
                "maximum_travel_distance",
            }
        }

    def apply_deterministic_constraints(
        self,
        constraints: Any,
        *,
        source: str = "postgresql_rule_engine",
    ) -> list[str]:
        """Copy only deterministic constraint values into PlanningFacts.

        No calculation occurs here. The value must already have been produced
        by the rule/constraint engine. Returns fields that changed.
        """
        changed: list[str] = []
        fields = getattr(constraints, "__dataclass_fields__", {})
        for name in fields:
            if name not in self.regulatory_value_fields():
                continue
            value = getattr(constraints, name, None)
            if value is None:
                continue
            before = self.get(name)
            if self.set_resolved_value(name, value, source=source):
                if before != value:
                    changed.append(name)
        return changed

    def set_resolved_value(
        self,
        field_name: str,
        value: Any,
        *,
        rule_id: str | None = None,
        regulation_id: str | None = None,
        unit: str | None = None,
        calculation: str | None = None,
        source: str = "postgresql_rule_engine",
    ) -> bool:
        """Set a regulatory value only when supplied by the deterministic engine.

        Existing authority/source facts are never silently overwritten. A
        conflicting value is recorded as an error and the existing value wins.
        """
        canonical = self._canonical_field_name(field_name)
        if not hasattr(self, canonical):
            self.values[canonical] = value
        else:
            current = getattr(self, canonical)
            if current is not None and current != value:
                self.regulatory_errors.append({
                    "type": "conflicting_resolved_value",
                    "field": canonical,
                    "existing": current,
                    "incoming": value,
                    "source": source,
                    "rule_id": rule_id,
                    "regulation_id": regulation_id,
                })
                return False
            setattr(self, canonical, value)

        self.regulatory_values[canonical] = value
        self.fact_sources[canonical] = source
        self.regulatory_trace.append({
            "field": canonical,
            "value": value,
            "unit": unit,
            "rule_id": rule_id,
            "regulation_id": regulation_id,
            "calculation": calculation,
            "source": source,
        })
        return True

    def record_missing_input(
        self,
        field_name: str,
        *,
        reason: str = "Required by an applicable regulatory rule.",
        rule_id: str | None = None,
        regulation_id: str | None = None,
    ) -> None:
        canonical = self._canonical_field_name(field_name)
        if canonical not in self.regulatory_missing_inputs:
            self.regulatory_missing_inputs.append(canonical)
        question = {
            "field": canonical,
            "reason": reason,
            "rule_id": rule_id,
            "regulation_id": regulation_id,
        }
        if question not in self.regulatory_user_questions:
            self.regulatory_user_questions.append(question)

    def record_required_approval(
        self,
        approval_type: str,
        *,
        authority: str | None = None,
        required: bool = True,
        available: bool | None = None,
        rule_id: str | None = None,
        regulation_id: str | None = None,
    ) -> None:
        item = {
            "approval_type": approval_type,
            "authority": authority,
            "required": required,
            "available": available,
            "rule_id": rule_id,
            "regulation_id": regulation_id,
        }
        if item not in self.regulatory_required_approvals:
            self.regulatory_required_approvals.append(item)
        if required and available is not True and item not in self.regulatory_pending_approvals:
            self.regulatory_pending_approvals.append(item)

    def record_dependency(
        self,
        *,
        from_rule_id: str,
        to_regulation: str | None = None,
        to_rule_id: str | None = None,
        reason: str = "Dependent regulatory provision.",
    ) -> None:
        item = {
            "from_rule_id": from_rule_id,
            "to_regulation": to_regulation,
            "to_rule_id": to_rule_id,
            "reason": reason,
        }
        if item not in self.regulatory_dependencies:
            self.regulatory_dependencies.append(item)

    def finalize_regulatory_resolution(self) -> None:
        if self.regulatory_errors:
            self.regulatory_resolution_status = "error"
        elif self.regulatory_pending_approvals:
            self.regulatory_resolution_status = "approval_required"
        elif self.regulatory_missing_inputs:
            self.regulatory_resolution_status = "needs_user_input"
        else:
            self.regulatory_resolution_status = "resolved"

    # ==========================================================
    # SERIALIZATION
    # ==========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Return all known planning facts.

        None values are omitted.

        False and zero are retained because they are valid facts.

        The returned dictionary is the canonical representation
        consumed by:
            - RuleConditionEngine
            - UDCPRRuleResolver
            - PlanningInputGate
            - deterministic constraint services
            - downstream design services
        """

        result: dict[str, Any] = {}

        # ------------------------------------------------------
        # Use dataclass fields instead of manually maintaining
        # hundreds of fields.
        # ------------------------------------------------------

        for field_info in (
            self.__dataclass_fields__.values()
        ):

            field_name = field_info.name

            value = getattr(
                self,
                field_name,
            )

            if value is None:
                continue

            result[field_name] = value

        # ------------------------------------------------------
        # Specialized facts override/add canonical facts.
        #
        # This preserves the existing behavior of the project.
        # ------------------------------------------------------

        if self.values:
            result.update(
                self.values
            )

        # Provenance metadata is intentionally kept separate
        # from canonical planning facts.
        result.pop("fact_sources", None)
        result.pop("fact_confidence", None)
        result.pop("fact_evidence", None)

        return result

    # ==========================================================
    # REQUIRED / PRESENT FACT HELPERS
    # ==========================================================

    def has(
        self,
        field_name: str,
    ) -> bool:
        """
        Return True when a fact has a meaningful value.

        False and zero are treated as valid supplied facts.
        """

        value = self.get(
            field_name
        )

        if value is None:
            return False

        if isinstance(
            value,
            str,
        ):

            return bool(
                value.strip()
            )

        if isinstance(
            value,
            (list, tuple, set, dict),
        ):

            return len(value) > 0

        return True

    # ==========================================================
    # UPDATE FROM DICTIONARY
    # ==========================================================

    def update_from_dict(
        self,
        data: dict[str, Any],
    ) -> "PlanningFacts":
        """
        Populate canonical PlanningFacts from a dictionary.

        Unknown fields are preserved in `values`.

        This is intentionally vocabulary-oriented and does not
        perform regulatory inference.
        """

        if not data:
            return self

        for key, value in data.items():
            if key == "fact_sources":
                if isinstance(value, dict):
                    self.fact_sources.update(value)
                continue

            if key == "fact_confidence":
                if isinstance(value, dict):
                    self.fact_confidence.update(value)
                continue

            if key == "fact_evidence":
                if isinstance(value, dict):
                    self.fact_evidence.update(value)
                continue

            canonical = self._canonical_field_name(
                key
            )

            if hasattr(
                self,
                canonical,
            ):

                setattr(
                    self,
                    canonical,
                    value,
                )

            else:

                self.values[
                    canonical
                ] = value

        return self

    # ==========================================================
    # CANONICAL FIELD NAME
    # ==========================================================

    @classmethod
    def _canonical_field_name(
        cls,
        field_name: str,
    ) -> str:
        """
        Resolve aliases without needing an instance.
        """

        aliases = {

            "plotArea":
                "plot_area",

            "plotWidth":
                "plot_width",

            "plotDepth":
                "plot_depth",

            "plotShape":
                "plot_shape",

            "roadWidth":
                "road_width",

            "roadWidths":
                "road_widths",

            "roadFrontageCount":
                "road_frontage_count",

            "roadFrontages":
                "road_frontages",

            "roadLocations":
                "road_locations",

            "accessAvailable":
                "access_available",

            "accessWidth":
                "access_width",

            "accessLength":
                "access_length",

            "planningAuthority":
                "planning_authority",

            "developmentAuthority":
                "development_authority",

            "landUseZone":
                "land_use_zone",

            "landUseClassification":
                "land_use_classification",

            "congestedArea":
                "congested_area",

            "buildingType":
                "building_type",

            "buildingUse":
                "building_use",

            "buildingHeight":
                "building_height",

            "numberOfFloors":
                "number_of_floors",

            "floorHeight":
                "floor_height",

            "maximumHeightM":
                "maximum_height_m",

            "maximum_height_m":
                "maximum_height_m",

            "maximumStoreys":
                "maximum_storeys",

            "maximum_storeys":
                "maximum_storeys",

            "maximumGroundCoverage":
                "maximum_ground_coverage",

            "maximum_ground_coverage":
                "maximum_ground_coverage",

            "selectedFloorCount":
                "selected_floor_count",

            "selected_floor_count":
                "selected_floor_count",

            "fireApprovedHeightM":
                "fire_approved_height_m",

            "fire_approved_height_m":
                "fire_approved_height_m",

            "totalFSI": "total_fsi",
            "total_fsi": "total_fsi",
            "incentiveFSI": "incentive_fsi",
            "incentive_fsi": "incentive_fsi",
            "maximumGroundCoverage": "maximum_ground_coverage",
            "maximum_ground_coverage": "maximum_ground_coverage",
            "carParkingRequired": "car_parking_required",
            "car_parking_required": "car_parking_required",
            "twoWheelerParkingRequired": "two_wheeler_parking_required",
            "two_wheeler_parking_required": "two_wheeler_parking_required",
            "visitorParkingRequired": "visitor_parking_required",
            "visitor_parking_required": "visitor_parking_required",
            "parkingAreaRequiredM2": "parking_area_required_m2",
            "parking_area_required_m2": "parking_area_required_m2",
            "fireAccessRequired": "fire_access_required",
            "fire_access_required": "fire_access_required",
            "fireLiftRequired": "fire_lift_required",
            "fire_lift_required": "fire_lift_required",
            "fireStaircaseRequired": "fire_staircase_required",
            "fire_staircase_required": "fire_staircase_required",
            "minimumExitCount": "minimum_exit_count",
            "minimum_exit_count": "minimum_exit_count",
            "minimumExitWidthM": "minimum_exit_width_m",
            "minimum_exit_width_m": "minimum_exit_width_m",
            "staircaseWidthM": "staircase_width_m",
            "staircase_width_m": "staircase_width_m",
            "corridorWidthM": "corridor_width_m",
            "corridor_width_m": "corridor_width_m",
            "accessibleEntranceRequired": "accessible_entrance_required",
            "accessible_entrance_required": "accessible_entrance_required",
            "rampRequired": "ramp_required",
            "ramp_required": "ramp_required",
            "rampWidthM": "ramp_width_m",
            "ramp_width_m": "ramp_width_m",
            "rampGradient": "ramp_gradient",
            "ramp_gradient": "ramp_gradient",
            "minimumOpenSpaceM2": "minimum_open_space_m2",
            "minimum_open_space_m2": "minimum_open_space_m2",
            "recreationalOpenSpaceM2": "recreational_open_space_m2",
            "recreational_open_space_m2": "recreational_open_space_m2",
            "amenitySpaceM2": "amenity_space_m2",
            "amenity_space_m2": "amenity_space_m2",
            "fireApprovalStatus": "fire_approval_status",
            "fireApprovalAuthority": "fire_approval_authority",
            "fireApprovedHeightSource": "fire_approved_height_source",
            "airportNocRequired": "airport_noc_required",
            "airportNocAvailable": "airport_noc_available",
            "airportNocNumber": "airport_noc_number",
            "airportClearanceHeightM": "airport_clearance_height_m",
            "heritageNocRequired": "heritage_noc_required",
            "heritageNocAvailable": "heritage_noc_available",
            "heritageNocNumber": "heritage_noc_number",
            "crzClearanceRequired": "crz_clearance_required",
            "crzClearanceAvailable": "crz_clearance_available",
            "crzClearanceNumber": "crz_clearance_number",
            "environmentalClearanceRequired": "environmental_clearance_required",
            "environmentalClearanceAvailable": "environmental_clearance_available",
            "environmentalClearanceNumber": "environmental_clearance_number",
            "forestClearanceRequired": "forest_clearance_required",
            "forestClearanceAvailable": "forest_clearance_available",
            "forestClearanceNumber": "forest_clearance_number",
            "defenceNocRequired": "defence_noc_required",
            "defenceNocAvailable": "defence_noc_available",
            "defenceNocNumber": "defence_noc_number",
            "railwayNocRequired": "railway_noc_required",
            "railwayNocAvailable": "railway_noc_available",
            "railwayNocNumber": "railway_noc_number",

            "mixedUse":
                "mixed_use",

            "groupHousing":
                "group_housing",

            "existingBuilding":
                "existing_building",

            "redevelopment":
                "redevelopment",

            "requestedUnits":
                "requested_units",

            "requested1BHKUnits":
                "requested_1bhk_units",

            "requested2BHKUnits":
                "requested_2bhk_units",

            "requested3BHKUnits":
                "requested_3bhk_units",

            "requested4BHKUnits":
                "requested_4bhk_units",

            "requestedUnitMix":
                "requested_unit_mix",

            "requestedResidentialArea":
                "requested_residential_area",

            "requestedCommercialArea":
                "requested_commercial_area",

            "requestedHeight":
                "requested_height",

            "requestedFloors":
                "requested_floors",

            "requestedFSI":
                "requested_fsi",

            "netPlotArea":
                "net_plot_area",

            "basicFSI":
                "basic_fsi",

            "premiumFSI":
                "premium_fsi",

            "tdrFSI":
                "tdr_fsi",

            "ancillaryFSI":
                "ancillary_fsi",

            "maximumFSI":
                "maximum_fsi",

            "permissibleFSI":
                "permissible_fsi",

            "airportRestriction":
                "airport_restriction",

            "railwayProximity":
                "railway_proximity",

            "floodLineStatus":
                "flood_line_status",

            "nallahOrWatercourse":
                "nallah_or_watercourse",

            "heritageRestriction":
                "heritage_restriction",

            "defenceRestriction":
                "defence_restriction",

            "waterSupplyAvailable":
                "water_supply_available",

            "sewerageAvailable":
                "sewerage_available",

            "parkingMode":
                "parking_mode",

            "tenementCarpetAreas":
                "tenement_carpet_areas",

            "sprinklerSystem":
                "sprinkler_system",

            "floorAreas":
                "floor_areas",

            "occupantLoad":
                "occupant_load",

            "staircaseCount":
                "staircase_count",

            "staircaseWidth":
                "staircase_width",

            "liftCount":
                "lift_count",

            "fireLiftCount":
                "fire_lift_count",

            "refugeAreaRequired":
                "refuge_area_required",
        }

        return aliases.get(
            field_name,
            field_name,
        )