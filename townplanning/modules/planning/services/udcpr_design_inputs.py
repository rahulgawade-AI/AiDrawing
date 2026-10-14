from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ==============================================================
# UDCPR DESIGN INPUT REQUIREMENT
# ==============================================================


@dataclass(frozen=True, slots=True)
class UDCPRInputRequirement:
    """
    Describes an input that may be required to determine, generate,
    or validate a building design under the applicable UDCPR rules.

    IMPORTANT
    ---------
    This registry describes INPUTS.

    It does NOT calculate:
        - FSI
        - setbacks
        - margins
        - parking
        - height
        - fire requirements
        - staircase requirements
        - lift requirements
        - refuge requirements
        - building geometry
        - room geometry

    Regulatory values must be obtained from the planning/rule
    discovery layer using the applicable UDCPR source.

    User-provided values and generated design-validation values
    are deliberately kept separate.
    """

    field: str
    question: str
    category: str
    reason: str

    required_for: tuple[str, ...] = ()
    source_regulations: tuple[str, ...] = ()
    conditional_on: tuple[str, ...] = ()

    # True when this can be supplied by the user/image extraction.
    design_input: bool = True

    # True when this value participates in regulatory rule selection.
    regulatory_input: bool = True


# ==============================================================
# CORE SITE / PLANNING INPUTS
# ==============================================================

CORE_UDCPR_INPUTS = (

    # ----------------------------------------------------------
    # SITE GEOMETRY
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="plot_area",
        question="What is the total plot area in square metres?",
        category="site",
        reason=(
            "Plot area is required for net plot area, FSI, "
            "open-space, amenity-space and development calculations."
        ),
        required_for=(
            "plot eligibility",
            "net plot area",
            "FSI",
            "built-up area",
            "open space",
            "amenity space",
        ),
        source_regulations=(
            "UDCPR 3.4.1",
            "UDCPR 3.5.1",
            "UDCPR 3.6",
            "UDCPR 3.7",
            "UDCPR 3.9",
            "UDCPR 6.2.1",
        ),
    ),

    UDCPRInputRequirement(
        field="plot_boundary",
        question="Is the plot boundary available and reliably established?",
        category="site",
        reason=(
            "Building placement, setbacks, margins and developable "
            "area depend on the actual plot boundary."
        ),
        required_for=(
            "building envelope",
            "setbacks",
            "margins",
            "site planning",
        ),
        source_regulations=(
            "UDCPR 6.2.1",
            "UDCPR 6.2.3",
        ),
    ),

    UDCPRInputRequirement(
        field="plot_width",
        question="What is the plot width in metres?",
        category="site",
        reason=(
            "Plot width affects plot eligibility, building envelope "
            "and setback calculations."
        ),
        required_for=(
            "plot eligibility",
            "building footprint",
            "setbacks",
        ),
        source_regulations=(
            "UDCPR 3.7 Table 3D",
            "UDCPR 6.2.1 Table 6D",
        ),
    ),

    UDCPRInputRequirement(
        field="plot_depth",
        question="What is the plot depth in metres?",
        category="site",
        reason=(
            "Plot depth is required to determine whether the required "
            "setbacks and building envelope can accommodate the design."
        ),
        required_for=(
            "building envelope",
            "building footprint",
            "setbacks",
        ),
        source_regulations=(
            "UDCPR 6.2.1 Table 6D",
            "UDCPR 3.7",
        ),
    ),

    UDCPRInputRequirement(
        field="plot_shape",
        question="What is the shape of the plot?",
        category="site",
        reason=(
            "Actual plot geometry affects the buildable envelope "
            "and placement of the building."
        ),
        required_for=(
            "building envelope",
            "site planning",
            "building placement",
        ),
        source_regulations=(
            "UDCPR 6.2.1",
            "UDCPR 6.2.3",
        ),
    ),

    UDCPRInputRequirement(
        field="plot_side_lengths",
        question="What are the lengths of all plot boundary sides?",
        category="site",
        reason=(
            "Irregular plots require actual side geometry to construct "
            "the building envelope accurately."
        ),
        required_for=(
            "plot geometry",
            "building envelope",
            "site planning",
        ),
        source_regulations=(
            "UDCPR 6.2.1",
            "UDCPR 6.2.3",
        ),
    ),

    UDCPRInputRequirement(
        field="north_direction",
        question="What is the north direction/orientation of the plot?",
        category="site",
        reason=(
            "Orientation is required for building orientation and "
            "daylight/ventilation optimisation."
        ),
        required_for=(
            "building orientation",
            "daylight",
            "ventilation",
            "site planning",
        ),
        regulatory_input=False,
    ),

    # ----------------------------------------------------------
    # LOCATION / AUTHORITY
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="state",
        question="Which state is the plot located in?",
        category="location",
        reason="The supplied planning framework is Maharashtra UDCPR.",
        required_for=(
            "regulation jurisdiction",
        ),
        source_regulations=(
            "UDCPR",
        ),
    ),

    UDCPRInputRequirement(
        field="district",
        question="Which district is the plot located in?",
        category="location",
        reason=(
            "Regional-plan and area-specific provisions can depend "
            "on the district and planning area."
        ),
        required_for=(
            "regional-plan rules",
            "area-specific rules",
        ),
        source_regulations=(
            "UDCPR Chapter 5",
        ),
    ),

    UDCPRInputRequirement(
        field="city",
        question="Which city is the plot located in?",
        category="location",
        reason=(
            "Applicable planning authority, zoning and certain "
            "development provisions depend on location."
        ),
        required_for=(
            "planning authority",
            "zoning",
            "FSI",
            "parking",
        ),
        source_regulations=(
            "UDCPR 4.1",
            "UDCPR 8.2.2 Table 8C",
        ),
    ),

    UDCPRInputRequirement(
        field="municipality",
        question="Which municipality/local body covers the plot?",
        category="authority",
        reason=(
            "Local planning jurisdiction is required to select "
            "the applicable regulatory provisions."
        ),
        required_for=(
            "planning authority",
            "development permission",
        ),
        source_regulations=(
            "UDCPR 2.1",
            "UDCPR 6.1",
        ),
    ),

    UDCPRInputRequirement(
        field="planning_authority",
        question="Which planning authority has jurisdiction over the plot?",
        category="authority",
        reason=(
            "Several UDCPR provisions vary according to the planning "
            "authority or applicable area."
        ),
        required_for=(
            "FSI",
            "parking",
            "zoning",
            "development permission",
        ),
        source_regulations=(
            "UDCPR 2.1",
            "UDCPR 6.1",
            "UDCPR 8.2.2",
        ),
    ),

    UDCPRInputRequirement(
        field="development_plan_status",
        question=(
            "Is the plot covered by a sanctioned Development Plan, "
            "Regional Plan or other applicable planning proposal?"
        ),
        category="planning",
        reason=(
            "Land use, reservations, roads and road widening depend "
            "on the applicable planning proposal."
        ),
        required_for=(
            "zoning",
            "reservation",
            "road widening",
            "net plot area",
        ),
        source_regulations=(
            "UDCPR 4.1",
            "UDCPR 3.9",
        ),
    ),

    UDCPRInputRequirement(
        field="development_plan_number",
        question="What is the applicable Development Plan/reference number?",
        category="planning",
        reason=(
            "The applicable development-plan document may be required "
            "to resolve zoning and reservations."
        ),
        required_for=(
            "planning verification",
            "zoning verification",
            "reservation verification",
        ),
        source_regulations=(
            "UDCPR 4.1",
            "UDCPR 3.9",
        ),
    ),

    UDCPRInputRequirement(
        field="regional_plan_status",
        question="Is the plot governed by an applicable Regional Plan?",
        category="planning",
        reason=(
            "Regional Plan provisions can affect land use, reservation "
            "and development eligibility."
        ),
        required_for=(
            "regional-plan rules",
            "land-use verification",
        ),
        source_regulations=(
            "UDCPR Chapter 5",
        ),
    ),

    # ----------------------------------------------------------
    # ZONING
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="zone",
        question="What is the applicable land-use zone?",
        category="zoning",
        reason=(
            "The proposed use must conform to the applicable "
            "land-use classification."
        ),
        required_for=(
            "permissible use",
            "FSI",
            "setbacks",
            "development eligibility",
        ),
        source_regulations=(
            "UDCPR 4.1",
            "UDCPR 4.2",
            "UDCPR 4.3",
            "UDCPR 4.4",
            "UDCPR 4.7",
            "UDCPR 4.8",
        ),
    ),

    UDCPRInputRequirement(
        field="land_use_classification",
        question="What is the exact land-use classification shown in the plan?",
        category="zoning",
        reason=(
            "Exact classification is required where zone equivalency "
            "or use-specific provisions apply."
        ),
        required_for=(
            "permissible use",
            "zone equivalency",
        ),
        source_regulations=(
            "UDCPR 4.1",
            "UDCPR 4.2",
        ),
    ),

    # ----------------------------------------------------------
    # ROAD / ACCESS
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="road_frontages",
        question=(
            "Which sides of the plot abut roads and what is the width "
            "of each abutting road?"
        ),
        category="road",
        reason=(
            "Road width and frontage affect setbacks, FSI, access "
            "and building potential."
        ),
        required_for=(
            "FSI",
            "front setback",
            "roadside margin",
            "access",
            "building potential",
        ),
        source_regulations=(
            "UDCPR 3.2",
            "UDCPR 3.3",
            "UDCPR 6.2.1 Table 6D",
            "UDCPR 6.3",
        ),
    ),

    UDCPRInputRequirement(
        field="road_width",
        question="What is the width of the principal abutting road in metres?",
        category="road",
        reason=(
            "Road width is directly used in UDCPR tables for margins, "
            "FSI and other development requirements."
        ),
        required_for=(
            "FSI",
            "front setback",
            "margins",
            "building potential",
        ),
        source_regulations=(
            "UDCPR 6.2.1 Table 6D",
            "UDCPR 6.3",
            "UDCPR 3.2",
        ),
    ),

    UDCPRInputRequirement(
        field="access_available",
        question="Does the plot have a confirmed means of access?",
        category="access",
        reason=(
            "A plot must have an appropriate means of access."
        ),
        required_for=(
            "site access",
            "building design",
            "parking",
        ),
        source_regulations=(
            "UDCPR 3.2.1",
            "UDCPR 3.2.2",
            "UDCPR 3.3.14",
        ),
    ),

    UDCPRInputRequirement(
        field="access_width",
        question="What is the clear width of the access way in metres?",
        category="access",
        reason=(
            "Access-way width affects access compliance and building access."
        ),
        required_for=(
            "site access",
            "building access",
        ),
        source_regulations=(
            "UDCPR 3.2.2",
            "UDCPR 3.3.2",
        ),
    ),

    UDCPRInputRequirement(
        field="access_length",
        question="What is the length of the access way in metres?",
        category="access",
        reason=(
            "Access-way length can affect the permissible access arrangement."
        ),
        required_for=(
            "site access",
        ),
        source_regulations=(
            "UDCPR 3.2.2",
        ),
    ),

    UDCPRInputRequirement(
        field="access_location",
        question="Where is the access located relative to the plot boundary?",
        category="access",
        reason=(
            "Access position affects site circulation and building placement."
        ),
        required_for=(
            "site access",
            "site circulation",
            "parking",
        ),
        source_regulations=(
            "UDCPR 3.2",
            "UDCPR 3.3",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="road_classification",
        question="Is the abutting road a highway or classified road?",
        category="road",
        reason=(
            "Highways and classified roads can have additional access "
            "and building-line requirements."
        ),
        required_for=(
            "highway access",
            "building line",
            "road widening",
        ),
        source_regulations=(
            "UDCPR 3.1.6",
            "UDCPR 3.3.8",
        ),
    ),

    # ----------------------------------------------------------
    # RESERVATION / ROAD WIDENING
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="road_widening",
        question="Is the plot affected by proposed road widening?",
        category="reservation",
        reason=(
            "Road widening affects net plot area and building placement."
        ),
        required_for=(
            "net plot area",
            "FSI",
            "building envelope",
        ),
        source_regulations=(
            "UDCPR 3.9",
            "UDCPR 7.2",
        ),
    ),

    UDCPRInputRequirement(
        field="road_widening_area",
        question="What area of the plot is affected by road widening?",
        category="reservation",
        reason=(
            "Affected area must be accounted for in the effective "
            "development area."
        ),
        required_for=(
            "net plot area",
            "FSI",
        ),
        source_regulations=(
            "UDCPR 3.9",
            "UDCPR 7.2",
        ),
        conditional_on=("road_widening",),
    ),

    UDCPRInputRequirement(
        field="reservation_present",
        question="Is the plot affected by a Development/Regional Plan reservation?",
        category="reservation",
        reason=(
            "Reservations can affect developable area and FSI."
        ),
        required_for=(
            "net plot area",
            "FSI",
            "site planning",
        ),
        source_regulations=(
            "UDCPR 3.9",
            "UDCPR 3.10",
            "UDCPR 3.11",
        ),
    ),

    UDCPRInputRequirement(
        field="reservation_type",
        question="What type of reservation affects the plot?",
        category="reservation",
        reason="Different reservation types have different consequences.",
        required_for=(
            "reservation treatment",
            "net plot area",
        ),
        source_regulations=(
            "UDCPR 3.9",
            "UDCPR 3.10",
            "UDCPR 3.11",
        ),
        conditional_on=("reservation_present",),
    ),

    UDCPRInputRequirement(
        field="reservation_area",
        question="What area of the plot is under reservation?",
        category="reservation",
        reason=(
            "Reserved area is relevant to determination of net plot area."
        ),
        required_for=(
            "net plot area",
            "FSI",
        ),
        source_regulations=(
            "UDCPR 3.9",
        ),
        conditional_on=("reservation_present",),
    ),

    # ----------------------------------------------------------
    # PROJECT / DEVELOPMENT TYPE
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="project_type",
        question="What type of project is proposed?",
        category="project",
        reason=(
            "Applicable provisions differ for individual buildings, "
            "group housing, layouts and other development types."
        ),
        required_for=(
            "rule applicability",
            "building design",
        ),
        source_regulations=(
            "UDCPR 3.3.1",
            "UDCPR 3.4.1",
            "UDCPR 6.2.5",
        ),
    ),

    UDCPRInputRequirement(
        field="development_type",
        question="Is this new construction, redevelopment or reconstruction?",
        category="project",
        reason=(
            "Redevelopment provisions can differ from new-development "
            "provisions."
        ),
        required_for=(
            "FSI",
            "parking",
            "existing-building treatment",
        ),
        source_regulations=(
            "UDCPR 7.5",
            "UDCPR 7.6",
        ),
    ),

    UDCPRInputRequirement(
        field="existing_building",
        question="Is there an existing building on the plot?",
        category="existing_development",
        reason=(
            "Existing buildings affect redevelopment, existing FSI, "
            "parking and rehabilitation calculations."
        ),
        required_for=(
            "redevelopment",
            "existing FSI",
            "existing parking",
        ),
        source_regulations=(
            "UDCPR 7.5",
            "UDCPR 7.6",
            "UDCPR 8.2",
        ),
    ),

    UDCPRInputRequirement(
        field="existing_built_up_area",
        question="What is the authorised existing built-up area?",
        category="existing_development",
        reason=(
            "Existing authorised built-up area can affect redevelopment "
            "FSI entitlement."
        ),
        required_for=(
            "redevelopment FSI",
        ),
        source_regulations=(
            "UDCPR 7.5",
            "UDCPR 7.6.1",
            "UDCPR 7.6.2",
        ),
        conditional_on=("existing_building", "development_type"),
    ),

    UDCPRInputRequirement(
        field="existing_authorised_fsi",
        question="What FSI has already been authorised/consumed on the plot?",
        category="existing_development",
        reason=(
            "Existing authorised FSI can affect redevelopment entitlement."
        ),
        required_for=(
            "redevelopment FSI",
        ),
        source_regulations=(
            "UDCPR 7.5",
            "UDCPR 7.6",
        ),
        conditional_on=("existing_building", "development_type"),
    ),

    # ----------------------------------------------------------
    # BUILDING USE / OCCUPANCY
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="building_use",
        question="What is the proposed building use?",
        category="occupancy",
        reason=(
            "Building requirements vary according to use."
        ),
        required_for=(
            "setbacks",
            "parking",
            "fire",
            "stairs",
            "lifts",
            "room requirements",
        ),
        source_regulations=(
            "UDCPR Chapter 4",
            "UDCPR Chapter 6",
            "UDCPR Chapter 8",
            "UDCPR Chapter 9",
        ),
    ),

    UDCPRInputRequirement(
        field="occupancy",
        question="What is the building occupancy classification?",
        category="occupancy",
        reason=(
            "Occupant load, exits, parking and fire provisions depend "
            "on occupancy."
        ),
        required_for=(
            "occupant load",
            "exits",
            "parking",
            "fire safety",
        ),
        source_regulations=(
            "UDCPR 8.2.1",
            "UDCPR 9.28.5",
            "UDCPR 9.28.6",
        ),
    ),

    UDCPRInputRequirement(
        field="mixed_use",
        question="Is the proposed building mixed-use?",
        category="occupancy",
        reason=(
            "Mixed-use buildings can have separate requirements for "
            "different use components."
        ),
        required_for=(
            "mixed-use rules",
            "FSI",
            "parking",
            "fire",
        ),
        source_regulations=(
            "UDCPR 6.2.1",
            "UDCPR 6.2.2",
        ),
    ),

    # ----------------------------------------------------------
    # BUILDING HEIGHT / FLOORS
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="requested_height",
        question="What is the proposed or desired building height in metres?",
        category="building",
        reason=(
            "Building height can trigger different marginal-distance, "
            "lift, fire-lift and refuge-area requirements."
        ),
        required_for=(
            "margins",
            "lift requirement",
            "fire lift",
            "refuge area",
            "fire safety",
        ),
        source_regulations=(
            "UDCPR 6.2.3",
            "UDCPR 9.27",
            "UDCPR 9.29.6",
            "UDCPR 9.29.8",
        ),
    ),

    UDCPRInputRequirement(
        field="requested_floors",
        question="How many floors/storeys are proposed or desired?",
        category="building",
        reason=(
            "Number of floors affects building height, stairs, lifts, "
            "exits and floor-by-floor design."
        ),
        required_for=(
            "building height",
            "stairs",
            "lifts",
            "exits",
        ),
        source_regulations=(
            "UDCPR 9.27",
            "UDCPR 9.28",
        ),
    ),

    UDCPRInputRequirement(
        field="floor_height",
        question="What floor-to-floor height is proposed?",
        category="building",
        reason=(
            "Floor height is needed to determine overall building height."
        ),
        required_for=(
            "building height",
            "floor design",
        ),
        source_regulations=(
            "UDCPR 9.2",
            "UDCPR 9.27",
        ),
    ),

    # ----------------------------------------------------------
    # USER DESIGN PROGRAM
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="requested_units",
        question=(
            "How many dwelling units are required, if a fixed number "
            "is desired?"
        ),
        category="user_requirement",
        reason=(
            "A fixed unit count is a user design requirement. If omitted, "
            "the optimization engine should calculate the feasible unit "
            "count from area and regulatory constraints."
        ),
        required_for=(
            "unit planning",
            "parking",
            "occupant load",
        ),
        source_regulations=(
            "UDCPR 8.2.1",
            "UDCPR 9.28.5",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="requested_unit_mix",
        question=(
            "Is a specific dwelling-unit mix required, such as "
            "1BHK/2BHK/3BHK?"
        ),
        category="user_requirement",
        reason=(
            "The user may specify a preferred mix. If omitted, the "
            "optimizer should determine the feasible mix."
        ),
        required_for=(
            "unit planning",
            "parking",
        ),
        source_regulations=(
            "UDCPR 8.2.1 Table 8B",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="unit_carpet_requirements",
        question=(
            "What minimum and maximum carpet area is required for each "
            "dwelling-unit type?"
        ),
        category="user_requirement",
        reason=(
            "Unit carpet-area ranges define the design programme and "
            "are subsequently used for parking classification and "
            "unit-layout optimization."
        ),
        required_for=(
            "unit planning",
            "unit count",
            "unit mix",
            "parking",
        ),
        source_regulations=(
            "UDCPR 8.2.1 Table 8B",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="requested_residential_area",
        question=(
            "Is a specific residential area requirement desired?"
        ),
        category="user_requirement",
        reason=(
            "Residential area can be used as a project design objective."
        ),
        required_for=(
            "unit planning",
            "building planning",
        ),
        source_regulations=(
            "UDCPR 8.2.1",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="requested_commercial_area",
        question=(
            "What commercial area is proposed, if any?"
        ),
        category="user_requirement",
        reason=(
            "Commercial components can change occupancy, parking and "
            "mixed-use requirements."
        ),
        required_for=(
            "mixed-use planning",
            "parking",
            "occupancy",
        ),
        source_regulations=(
            "UDCPR 4.3",
            "UDCPR 4.4",
            "UDCPR 8.2.1",
        ),
        conditional_on=("mixed_use",),
        regulatory_input=False,
    ),

    # ----------------------------------------------------------
    # BUILDING ORGANISATION
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="number_of_buildings",
        question="How many buildings or wings are desired?",
        category="building",
        reason=(
            "Multiple buildings/wings require separate layout and "
            "building-separation planning."
        ),
        required_for=(
            "building layout",
            "building separation",
            "site planning",
        ),
        source_regulations=(
            "UDCPR 6.2.4",
            "UDCPR 6.2.5",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="building_orientation_preference",
        question="Is there a preferred building orientation?",
        category="design_preference",
        reason=(
            "Orientation can be optimized for daylight, ventilation, "
            "access and site conditions."
        ),
        required_for=(
            "building orientation",
            "daylight",
            "ventilation",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="maximize_fsi",
        question="Should the design attempt to maximize permissible FSI?",
        category="design_preference",
        reason="Controls the design optimization objective.",
        required_for=(
            "design optimization",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="maximize_usable_area",
        question="Should the design maximize usable residential area?",
        category="design_preference",
        reason="Controls the design optimization objective.",
        required_for=(
            "design optimization",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="optimize_daylight",
        question="Should natural daylight be optimized?",
        category="design_preference",
        reason="Controls room placement and facade/opening optimization.",
        required_for=(
            "building orientation",
            "room planning",
            "openings",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="optimize_ventilation",
        question="Should natural ventilation be optimized?",
        category="design_preference",
        reason="Controls room and opening placement.",
        required_for=(
            "room planning",
            "ventilation",
        ),
        regulatory_input=False,
    ),

    # ----------------------------------------------------------
    # SPECIAL SITE RESTRICTIONS
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="congested_area",
        question="Is the plot in a congested area?",
        category="special_condition",
        reason=(
            "Congested and non-congested areas can have different "
            "setback/margin provisions."
        ),
        required_for=(
            "setbacks",
            "margins",
            "FSI",
        ),
        source_regulations=(
            "UDCPR 6.1",
            "UDCPR 6.2",
        ),
    ),

    UDCPRInputRequirement(
        field="airport_restriction",
        question="Is the plot subject to airport height restrictions?",
        category="special_condition",
        reason=(
            "Airport CCZM restrictions can limit permissible building height."
        ),
        required_for=(
            "maximum height",
        ),
        source_regulations=(
            "UDCPR 3.1.9",
        ),
    ),

    UDCPRInputRequirement(
        field="site_elevation",
        question="What is the site elevation above mean sea level?",
        category="special_condition",
        reason=(
            "Where airport height is governed by CCZM, permissible "
            "height depends on site elevation."
        ),
        required_for=(
            "airport-controlled building height",
        ),
        source_regulations=(
            "UDCPR 3.1.9",
        ),
        conditional_on=("airport_restriction",),
    ),

    UDCPRInputRequirement(
        field="cczm_permissible_elevation",
        question=(
            "What maximum top elevation is permitted by the applicable "
            "Airport Authority CCZM?"
        ),
        category="special_condition",
        reason=(
            "Airport restrictions may be expressed using permissible "
            "top elevation."
        ),
        required_for=(
            "airport-controlled building height",
        ),
        source_regulations=(
            "UDCPR 3.1.9",
        ),
        conditional_on=("airport_restriction",),
    ),

    UDCPRInputRequirement(
        field="railway_proximity",
        question="Is the plot within 30 metres of a railway boundary?",
        category="special_condition",
        reason=(
            "Construction near railway boundaries can require Railway "
            "Authority treatment/NOC."
        ),
        required_for=(
            "railway restriction",
        ),
        source_regulations=(
            "UDCPR 3.1.4",
        ),
    ),

    UDCPRInputRequirement(
        field="natural_lake_proximity",
        question="Is the plot affected by a natural lake or its high-flood line?",
        category="special_condition",
        reason=(
            "Specific restrictions can apply around natural lakes."
        ),
        required_for=(
            "site eligibility",
            "building envelope",
        ),
        source_regulations=(
            "UDCPR 3.1.12",
        ),
    ),

    UDCPRInputRequirement(
        field="flood_line_status",
        question="Is the plot affected by blue or red flood lines?",
        category="special_condition",
        reason=(
            "Flood-line location changes whether and how construction "
            "can occur."
        ),
        required_for=(
            "site eligibility",
            "building envelope",
            "plinth",
        ),
        source_regulations=(
            "UDCPR 3.1.3",
        ),
    ),

    UDCPRInputRequirement(
        field="blue_flood_line_distance",
        question="What is the distance from the blue flood line in metres?",
        category="special_condition",
        reason="Required when flood-line restrictions apply.",
        required_for=(
            "building envelope",
            "flood restriction",
        ),
        source_regulations=(
            "UDCPR 3.1.3",
        ),
        conditional_on=("flood_line_status",),
    ),

    UDCPRInputRequirement(
        field="red_flood_line_distance",
        question="What is the distance from the red flood line in metres?",
        category="special_condition",
        reason="Required when flood-line restrictions apply.",
        required_for=(
            "building envelope",
            "flood restriction",
        ),
        source_regulations=(
            "UDCPR 3.1.3",
        ),
        conditional_on=("flood_line_status",),
    ),

    UDCPRInputRequirement(
        field="nallah_or_watercourse",
        question="Is there a nallah or watercourse affecting the plot?",
        category="special_condition",
        reason=(
            "Additional marginal-distance restrictions may apply."
        ),
        required_for=(
            "setbacks",
            "building envelope",
        ),
        source_regulations=(
            "UDCPR 3.1.3",
            "UDCPR 3.13.2",
        ),
    ),

    UDCPRInputRequirement(
        field="nallah_distance",
        question="What is the distance from the nallah/watercourse in metres?",
        category="special_condition",
        reason="Required when a nallah/watercourse affects the plot.",
        required_for=(
            "setbacks",
            "building envelope",
        ),
        source_regulations=(
            "UDCPR 3.13.2",
        ),
        conditional_on=("nallah_or_watercourse",),
    ),

    UDCPRInputRequirement(
        field="heritage_restriction",
        question="Is the plot affected by a heritage restriction?",
        category="special_condition",
        reason=(
            "Heritage restrictions can affect development and building design."
        ),
        required_for=(
            "site eligibility",
            "building design",
        ),
        source_regulations=(
            "UDCPR 3.1.10",
        ),
    ),

    UDCPRInputRequirement(
        field="defence_restriction",
        question="Is the plot affected by a Works of Defence restriction?",
        category="special_condition",
        reason=(
            "Defence restrictions can affect the developable portion."
        ),
        required_for=(
            "site eligibility",
            "building envelope",
        ),
        source_regulations=(
            "UDCPR 3.1.11",
        ),
    ),

    # ----------------------------------------------------------
    # GROUP HOUSING
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="group_housing",
        question="Is this a group housing scheme?",
        category="development_type",
        reason=(
            "Group housing has additional road, open-space, building "
            "separation and access considerations."
        ),
        required_for=(
            "internal roads",
            "open space",
            "building separation",
            "access",
        ),
        source_regulations=(
            "UDCPR 3.3.1",
            "UDCPR 3.3.2.C",
            "UDCPR 3.4.1",
            "UDCPR 6.2.5",
        ),
    ),

    UDCPRInputRequirement(
        field="internal_road_length",
        question="What is the length of each internal access/layout road?",
        category="development_type",
        reason=(
            "Internal-road requirements depend on development type "
            "and road length."
        ),
        required_for=(
            "internal road width",
            "group housing access",
        ),
        source_regulations=(
            "UDCPR 3.3.2",
        ),
        conditional_on=("group_housing",),
    ),

    # ----------------------------------------------------------
    # FIRE / LIFE SAFETY INPUTS
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="floor_areas",
        question="What are the floor areas of the proposed floors?",
        category="fire",
        reason=(
            "Floor area is used for occupant-load and exit calculations."
        ),
        required_for=(
            "occupant load",
            "number of exits",
            "exit width",
            "fire planning",
        ),
        source_regulations=(
            "UDCPR 9.28.3",
            "UDCPR 9.28.5",
            "UDCPR 9.28.6",
        ),
        design_input=False,
        regulatory_input=True,
    ),

    UDCPRInputRequirement(
        field="occupant_load",
        question="What is the calculated occupant load for each floor?",
        category="fire",
        reason=(
            "Exit requirements are determined using occupant load."
        ),
        required_for=(
            "exit count",
            "exit width",
            "staircase capacity",
        ),
        source_regulations=(
            "UDCPR 9.28.3",
            "UDCPR 9.28.5",
            "UDCPR 9.28.6",
        ),
        design_input=False,
        regulatory_input=True,
    ),

    UDCPRInputRequirement(
        field="sprinkler_system",
        question="Will the building have a sprinkler system throughout?",
        category="fire",
        reason=(
            "Sprinkler provision can affect applicable fire-planning criteria."
        ),
        required_for=(
            "travel distance",
            "fire design",
        ),
        source_regulations=(
            "UDCPR 9.28.4",
        ),
    ),

    # ----------------------------------------------------------
    # PARKING
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="tenement_carpet_areas",
        question=(
            "What is the carpet area of each residential tenement "
            "or applicable tenement-size category?"
        ),
        category="parking",
        reason=(
            "Residential parking requirements use tenement carpet-area "
            "categories."
        ),
        required_for=(
            "car parking",
            "two-wheeler parking",
            "visitor parking",
        ),
        source_regulations=(
            "UDCPR 8.2.1 Table 8B",
        ),
    ),

    UDCPRInputRequirement(
        field="existing_parking_spaces",
        question="How many authorised existing parking spaces are available?",
        category="parking",
        reason=(
            "Existing parking can affect redevelopment/additional "
            "development parking calculations."
        ),
        required_for=(
            "redevelopment parking",
            "additional development parking",
        ),
        source_regulations=(
            "UDCPR 8.1",
            "UDCPR 8.2",
        ),
        conditional_on=("existing_building",),
    ),

    UDCPRInputRequirement(
        field="parking_mode",
        question=(
            "Will parking be open, basement, stilt, podium or mechanised?"
        ),
        category="parking",
        reason=(
            "Parking arrangement affects parking layout, ramps and "
            "building planning."
        ),
        required_for=(
            "parking layout",
            "ramp design",
        ),
        source_regulations=(
            "UDCPR 8.1.1",
            "UDCPR 9.11",
            "UDCPR 9.12",
            "UDCPR 9.13",
        ),
    ),

    UDCPRInputRequirement(
        field="parking_preference",
        question=(
            "Is there a preferred parking arrangement or parking "
            "capacity objective?"
        ),
        category="design_preference",
        reason=(
            "Parking can be treated as a design optimization objective."
        ),
        required_for=(
            "site planning",
            "parking layout",
        ),
        regulatory_input=False,
    ),

    # ----------------------------------------------------------
    # LIGHT / VENTILATION / ROOMS
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="room_areas",
        question=(
            "What are the proposed areas of habitable rooms and kitchens?"
        ),
        category="building_parts",
        reason=(
            "Room area is used when checking natural lighting and ventilation."
        ),
        required_for=(
            "natural lighting",
            "natural ventilation",
        ),
        source_regulations=(
            "UDCPR 9.20.1",
        ),
        design_input=False,
        regulatory_input=True,
    ),

    UDCPRInputRequirement(
        field="room_depths",
        question="What are the proposed room depths?",
        category="building_parts",
        reason=(
            "Room depth is relevant to natural lighting/ventilation checks."
        ),
        required_for=(
            "natural lighting",
            "ventilation",
        ),
        source_regulations=(
            "UDCPR 9.20.1",
        ),
        design_input=False,
        regulatory_input=True,
    ),

    UDCPRInputRequirement(
        field="bathroom_count",
        question="How many bathrooms and water closets are proposed?",
        category="building_parts",
        reason=(
            "Bathroom/WC dimensions, ventilation and drainage must be checked."
        ),
        required_for=(
            "sanitation",
            "ventilation",
            "drainage",
        ),
        source_regulations=(
            "UDCPR 9.4",
        ),
        regulatory_input=False,
    ),

    # ----------------------------------------------------------
    # SERVICES
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="water_supply_available",
        question="Is an approved water-supply arrangement available?",
        category="services",
        reason=(
            "Water services and storage arrangements need to be "
            "incorporated in building design."
        ),
        required_for=(
            "water services",
            "building services",
        ),
        source_regulations=(
            "UDCPR 9.21",
            "UDCPR 9.25",
        ),
    ),

    UDCPRInputRequirement(
        field="sewerage_available",
        question="Is a public sewerage/drainage connection available?",
        category="services",
        reason=(
            "Where public sewerage is unavailable, an appropriate "
            "alternative must be planned."
        ),
        required_for=(
            "drainage",
            "sanitation",
        ),
        source_regulations=(
            "UDCPR 9.4.3",
            "UDCPR 9.25",
        ),
    ),
)


# ==============================================================
# HEIGHT-DEPENDENT INPUTS
# ==============================================================

HEIGHT_DEPENDENT_INPUTS = (

    UDCPRInputRequirement(
        field="requested_height",
        question="What is the proposed maximum building height in metres?",
        category="height",
        reason=(
            "Height determines whether higher-height margin, lift, "
            "fire-lift and refuge-area provisions are triggered."
        ),
        required_for=(
            "margins",
            "lifts",
            "fire lift",
            "refuge area",
        ),
        source_regulations=(
            "UDCPR 6.2.3",
            "UDCPR 9.27",
            "UDCPR 9.29.6",
            "UDCPR 9.29.8",
        ),
    ),

    UDCPRInputRequirement(
        field="proposed_floor_population",
        question=(
            "What is the expected population/occupant load on each floor?"
        ),
        category="height",
        reason=(
            "Lift planning depends on occupancy/population and building height."
        ),
        required_for=(
            "lift number",
            "lift capacity",
        ),
        source_regulations=(
            "UDCPR 9.27.1",
        ),
        design_input=False,
        regulatory_input=True,
    ),
)


# ==============================================================
# DESIGN-PROGRAM INPUTS
#
# These are user requirements/preferences, NOT regulatory values.
# ===============================================================

DESIGN_PROGRAM_INPUTS = (

    UDCPRInputRequirement(
        field="unit_carpet_requirements",
        question=(
            "What minimum and maximum carpet area should each unit type have?"
        ),
        category="unit_program",
        reason=(
            "The optimizer uses these limits to determine feasible unit "
            "count and unit mix."
        ),
        required_for=(
            "unit count",
            "unit mix",
            "unit geometry",
            "parking",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="minimum_units",
        question="Is there a minimum number of dwelling units required?",
        category="unit_program",
        reason=(
            "Constrains the optimization without forcing an exact unit count."
        ),
        required_for=(
            "unit optimization",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="maximum_units",
        question="Is there a maximum number of dwelling units allowed?",
        category="unit_program",
        reason=(
            "Constrains the optimization without requiring a fixed unit count."
        ),
        required_for=(
            "unit optimization",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="unit_mix_preference",
        question=(
            "Is there a preferred percentage/count mix of 1BHK, 2BHK, "
            "3BHK or other units?"
        ),
        category="unit_program",
        reason=(
            "Allows the optimizer to balance the requested market/program "
            "mix against the feasible building envelope."
        ),
        required_for=(
            "unit mix",
            "unit optimization",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="carpet_area_unit",
        question="What unit should be used for the requested carpet areas?",
        category="unit_program",
        reason="Allows consistent conversion and validation.",
        required_for=(
            "unit area validation",
            "parking classification",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="parking_spaces_required",
        question="Is a specific number of parking spaces desired?",
        category="parking_program",
        reason=(
            "A user parking target can be treated as an optimization "
            "objective or constraint."
        ),
        required_for=(
            "parking planning",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="visitor_parking_required",
        question="Is visitor parking required as a project objective?",
        category="parking_program",
        reason="Used during parking/site-layout optimization.",
        required_for=(
            "parking planning",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="two_wheeler_parking_required",
        question="Is two-wheeler parking required as a project objective?",
        category="parking_program",
        reason="Used during parking/site-layout optimization.",
        required_for=(
            "parking planning",
        ),
        regulatory_input=False,
    ),

    # ----------------------------------------------------------
    # BUILDING CORE
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="lift_required",
        question="Is a lift required or desired?",
        category="vertical_circulation",
        reason=(
            "Lift requirements must be determined from the applicable "
            "building height/use rules; the user may also express a preference."
        ),
        required_for=(
            "core planning",
            "vertical circulation",
        ),
        source_regulations=(
            "UDCPR 9.27",
        ),
    ),

    UDCPRInputRequirement(
        field="lift_count_preference",
        question="Is a preferred number of passenger lifts specified?",
        category="vertical_circulation",
        reason=(
            "Used as a design preference subject to regulatory validation."
        ),
        required_for=(
            "core planning",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="staircase_count_preference",
        question="Is a preferred number of staircases specified?",
        category="vertical_circulation",
        reason=(
            "Used as a design preference; actual requirement is determined "
            "by the applicable fire/life-safety rules."
        ),
        required_for=(
            "core planning",
        ),
        regulatory_input=False,
    ),

    UDCPRInputRequirement(
        field="refuge_area_preference",
        question="Is a refuge area required by the applicable design scenario?",
        category="fire",
        reason=(
            "Refuge requirements must be determined from the applicable "
            "height/fire provisions and then incorporated into the design."
        ),
        required_for=(
            "core planning",
            "fire planning",
        ),
        source_regulations=(
            "UDCPR 9.29.8",
        ),
    ),

    # ----------------------------------------------------------
    # OPEN SPACE / AMENITY
    # ----------------------------------------------------------

    UDCPRInputRequirement(
        field="recreational_open_space_preference",
        question="Is recreational open space required for the project?",
        category="open_space",
        reason=(
            "Open-space requirements are determined from the applicable "
            "planning rules and project characteristics."
        ),
        required_for=(
            "site planning",
            "open-space planning",
        ),
        source_regulations=(
            "UDCPR 3.4.1",
        ),
    ),

    UDCPRInputRequirement(
        field="amenity_space_preference",
        question="Is amenity space applicable to this project?",
        category="open_space",
        reason=(
            "Amenity-space applicability depends on project size and "
            "applicable UDCPR provisions."
        ),
        required_for=(
            "site planning",
            "amenity planning",
        ),
        source_regulations=(
            "UDCPR 3.6",
            "UDCPR 3.7",
        ),
    ),
)


# ==============================================================
# DESIGN VALIDATION FIELDS
#
# These are NOT normally user inputs.
#
# They are produced by the deterministic design engine and then
# checked against the regulatory constraints discovered from UDCPR.
# ==============================================================

DESIGN_VALIDATION_FIELDS = (

    # ----------------------------------------------------------
    # SITE / AREA
    # ----------------------------------------------------------

    "net_plot_area",

    "building_footprint",

    "built_up_area",

    "total_built_up_area",

    "fsi_area",

    "basic_fsi_area",

    "premium_fsi_area",

    "tdr_fsi_area",

    "ancillary_fsi_area",

    "non_fsi_area",

    # ----------------------------------------------------------
    # SETBACKS / MARGINS
    # ----------------------------------------------------------

    "front_setback",

    "rear_setback",

    "side_setback_left",

    "side_setback_right",

    "roadside_margin",

    "building_line",

    "building_separation",

    # ----------------------------------------------------------
    # HEIGHT
    # ----------------------------------------------------------

    "building_height",

    "number_of_floors",

    "floor_to_floor_height",

    # ----------------------------------------------------------
    # RESIDENTIAL UNITS
    # ----------------------------------------------------------

    "total_units",

    "units_1bhk",

    "units_2bhk",

    "units_3bhk",

    "units_other",

    "unit_carpet_area",

    "total_carpet_area",

    "residential_area",

    # ----------------------------------------------------------
    # CIRCULATION
    # ----------------------------------------------------------

    "corridor_area",

    "corridor_width",

    "staircase_count",

    "staircase_width",

    "staircase_area",

    "lift_count",

    "lift_capacity",

    "lift_area",

    "fire_lift_count",

    "fire_lift_area",

    "vertical_core_area",

    "service_shaft_area",

    # ----------------------------------------------------------
    # FIRE / LIFE SAFETY
    # ----------------------------------------------------------

    "exit_count",

    "exit_width",

    "travel_distance",

    "occupant_load",

    "floor_population",

    "refuge_area",

    "fire_access",

    # ----------------------------------------------------------
    # PARKING
    # ----------------------------------------------------------

    "parking_car_count",

    "parking_two_wheeler_count",

    "visitor_parking_count",

    "parking_area",

    "parking_drive_width",

    "parking_ramp_width",

    "parking_ramp_slope",

    "parking_turning_radius",

    # ----------------------------------------------------------
    # ROOM / UNIT VALIDATION
    # ----------------------------------------------------------

    "room_area",

    "room_depth",

    "room_width",

    "living_area",

    "dining_area",

    "kitchen_area",

    "bedroom_area",

    "master_bedroom_area",

    "bathroom_area",

    "water_closet_area",

    "toilet_area",

    "balcony_area",

    "internal_circulation_area",

    # ----------------------------------------------------------
    # LIGHT / VENTILATION
    # ----------------------------------------------------------

    "room_opening_area",

    "window_area",

    "ventilation_area",

    "ventilation_shaft_area",

    "light_shaft_area",

    # ----------------------------------------------------------
    # OPEN SPACE / AMENITY
    # ----------------------------------------------------------

    "recreational_open_space_m2",

    "amenity_space_m2",

    "landscape_area",

    # ----------------------------------------------------------
    # SERVICES
    # ----------------------------------------------------------

    "water_storage_area",

    "electric_substation_area",

    "transformer_area",

    "service_area",

    "garbage_room_area",

    # ----------------------------------------------------------
    # DESIGN QUALITY
    # ----------------------------------------------------------

    "residual_space_area",

    "unusable_space_area",

    "circulation_percent",

    "core_percent",

    "residential_utilization_percent",

    "floor_utilization_percent",

    "plot_utilization_percent",

    "carpet_to_builtup_ratio",
)


# ==============================================================
# REGISTRY
# ==============================================================

ALL_UDCPR_DESIGN_INPUTS = (
    CORE_UDCPR_INPUTS
    + HEIGHT_DEPENDENT_INPUTS
    + DESIGN_PROGRAM_INPUTS
)


INPUT_BY_FIELD = {
    item.field: item
    for item in ALL_UDCPR_DESIGN_INPUTS
}


# ==============================================================
# PUBLIC API
# ==============================================================

def get_input_requirement(
    field: str,
) -> UDCPRInputRequirement | None:

    return INPUT_BY_FIELD.get(field)


def get_all_input_requirements() -> tuple[
    UDCPRInputRequirement,
    ...
]:

    return ALL_UDCPR_DESIGN_INPUTS


def get_requirements_for_category(
    category: str,
) -> tuple[UDCPRInputRequirement, ...]:

    return tuple(
        item
        for item in ALL_UDCPR_DESIGN_INPUTS
        if item.category == category
    )


def get_design_input_requirements() -> tuple[
    UDCPRInputRequirement,
    ...
]:

    return tuple(
        item
        for item in ALL_UDCPR_DESIGN_INPUTS
        if item.design_input
    )


def get_regulatory_input_requirements() -> tuple[
    UDCPRInputRequirement,
    ...
]:

    return tuple(
        item
        for item in ALL_UDCPR_DESIGN_INPUTS
        if item.regulatory_input
    )


def get_design_validation_fields() -> tuple[str, ...]:

    return DESIGN_VALIDATION_FIELDS


def requirement_to_dict(
    item: UDCPRInputRequirement,
) -> dict[str, Any]:

    return {
        "field": item.field,
        "question": item.question,
        "category": item.category,
        "reason": item.reason,
        "required_for": list(item.required_for),
        "source_regulations": list(
            item.source_regulations
        ),
        "conditional_on": list(
            item.conditional_on
        ),
        "design_input": item.design_input,
        "regulatory_input": item.regulatory_input,
    }


def get_all_requirements_as_dicts() -> list[dict[str, Any]]:

    return [
        requirement_to_dict(item)
        for item in ALL_UDCPR_DESIGN_INPUTS
    ]


# ==============================================================
# REQUIRED USER INPUT LOGIC
# ==============================================================

def _condition_is_satisfied(
    requirement: UDCPRInputRequirement,
    facts: Any,
) -> bool:

    if not requirement.conditional_on:
        return True

    for condition_field in requirement.conditional_on:

        value = getattr(
            facts,
            condition_field,
            None,
        )

        # A condition is considered satisfied when the corresponding
        # boolean is True or the value is non-empty/non-None.
        if isinstance(value, bool):

            if not value:
                return False

        elif value is None:

            return False

        elif value == "":

            return False

    return True


def get_applicable_requirements(
    facts: Any,
) -> tuple[UDCPRInputRequirement, ...]:

    result = []

    for item in ALL_UDCPR_DESIGN_INPUTS:

        if not _condition_is_satisfied(
            item,
            facts,
        ):
            continue

        result.append(item)

    return tuple(result)


def get_missing_user_inputs(
    facts: Any,
) -> tuple[UDCPRInputRequirement, ...]:
    """
    Return user/design inputs that are currently missing.

    This function deliberately does NOT mark generated design
    validation fields as missing user input.

    It also does not assume requested_units is mandatory.

    requested_units=None means:

        "optimizer should determine feasible unit count"

    rather than:

        "information missing from user".
    """

    missing = []

    for item in get_applicable_requirements(facts):

        if not item.design_input:
            continue

        # These are optional optimization controls.
        optional_fields = {
            "requested_units",
            "requested_unit_mix",
            "requested_residential_area",
            "requested_commercial_area",
            "minimum_units",
            "maximum_units",
            "unit_mix_preference",
            "parking_preference",
            "parking_spaces_required",
            "visitor_parking_required",
            "two_wheeler_parking_required",
            "lift_count_preference",
            "staircase_count_preference",
            "refuge_area_preference",
            "recreational_open_space_preference",
            "amenity_space_preference",
            "building_orientation_preference",
            "maximize_fsi",
            "maximize_usable_area",
            "optimize_daylight",
            "optimize_ventilation",
        }

        if item.field in optional_fields:
            continue

        value = getattr(
            facts,
            item.field,
            None,
        )

        if value is None:
            missing.append(item)
            continue

        if isinstance(value, str) and not value.strip():
            missing.append(item)
            continue

        if isinstance(value, (list, dict)) and not value:
            missing.append(item)

    return tuple(missing)


# ==============================================================
# IMAGE EXTRACTION CANDIDATES
# ==============================================================

# These are fields that can potentially be extracted from a plot
# image/site plan. Extraction confidence must be evaluated by the
# image/document extraction layer.
#
# IMPORTANT:
# An image extraction result must NOT automatically become a trusted
# planning fact when confidence is insufficient.
# ==============================================================

IMAGE_EXTRACTABLE_FIELDS = (
    "plot_boundary",
    "plot_area",
    "plot_width",
    "plot_depth",
    "plot_shape",
    "plot_side_lengths",
    "north_direction",
    "road_frontages",
    "road_width",
    "access_available",
    "access_width",
    "access_length",
    "road_classification",
    "road_widening",
    "road_widening_area",
    "reservation_present",
    "reservation_type",
    "reservation_area",
    "airport_restriction",
    "railway_proximity",
    "natural_lake_proximity",
    "flood_line_status",
    "blue_flood_line_distance",
    "red_flood_line_distance",
    "nallah_or_watercourse",
    "nallah_distance",
    "heritage_restriction",
    "defence_restriction",
)


def is_image_extractable(
    field: str,
) -> bool:

    return field in IMAGE_EXTRACTABLE_FIELDS


def get_image_extractable_requirements() -> tuple[
    UDCPRInputRequirement,
    ...
]:

    return tuple(
        item
        for item in ALL_UDCPR_DESIGN_INPUTS
        if item.field in IMAGE_EXTRACTABLE_FIELDS
    )


# ==============================================================
# DESIGN GENERATION INPUTS
# ==============================================================

DESIGN_GENERATION_FIELDS = (
    "plot_area",
    "plot_boundary",
    "plot_width",
    "plot_depth",
    "plot_shape",
    "plot_side_lengths",
    "north_direction",

    "road_frontages",
    "road_width",
    "access_available",
    "access_width",
    "access_length",
    "access_location",

    "zone",
    "land_use_classification",
    "planning_authority",

    "road_widening",
    "road_widening_area",

    "reservation_present",
    "reservation_type",
    "reservation_area",

    "project_type",
    "development_type",
    "existing_building",

    "building_use",
    "occupancy",
    "mixed_use",

    "requested_height",
    "requested_floors",
    "floor_height",

    "requested_units",
    "requested_unit_mix",
    "unit_carpet_requirements",

    "requested_residential_area",
    "requested_commercial_area",

    "number_of_buildings",
    "group_housing",

    "parking_mode",

    "maximize_fsi",
    "maximize_usable_area",
    "optimize_daylight",
    "optimize_ventilation",
)


def get_design_generation_fields() -> tuple[str, ...]:

    return DESIGN_GENERATION_FIELDS


# ==============================================================
# VALIDATION / SAFETY HELPERS
# ==============================================================

def is_design_validation_field(
    field: str,
) -> bool:

    return field in DESIGN_VALIDATION_FIELDS


def is_required_user_field(
    field: str,
) -> bool:

    requirement = get_input_requirement(field)

    if requirement is None:
        return False

    if not requirement.design_input:
        return False

    optional_fields = {
        "requested_units",
        "requested_unit_mix",
        "requested_residential_area",
        "requested_commercial_area",
        "minimum_units",
        "maximum_units",
        "unit_mix_preference",
        "parking_preference",
        "parking_spaces_required",
        "visitor_parking_required",
        "two_wheeler_parking_required",
        "lift_count_preference",
        "staircase_count_preference",
        "refuge_area_preference",
        "recreational_open_space_preference",
        "amenity_space_preference",
        "building_orientation_preference",
        "maximize_fsi",
        "maximize_usable_area",
        "optimize_daylight",
        "optimize_ventilation",
    }

    return field not in optional_fields


# ==============================================================
# FIELD GROUPS FOR PLANNING PIPELINE
# ==============================================================

FIELD_GROUPS = {

    "site": (
        "plot_area",
        "plot_boundary",
        "plot_width",
        "plot_depth",
        "plot_shape",
        "plot_side_lengths",
        "north_direction",
    ),

    "location": (
        "state",
        "district",
        "city",
        "municipality",
        "planning_authority",
        "development_plan_status",
        "development_plan_number",
        "regional_plan_status",
    ),

    "zoning": (
        "zone",
        "land_use_classification",
    ),

    "road_access": (
        "road_frontages",
        "road_width",
        "access_available",
        "access_width",
        "access_length",
        "access_location",
        "road_classification",
    ),

    "reservation": (
        "road_widening",
        "road_widening_area",
        "reservation_present",
        "reservation_type",
        "reservation_area",
    ),

    "special_restrictions": (
        "congested_area",
        "airport_restriction",
        "site_elevation",
        "cczm_permissible_elevation",
        "railway_proximity",
        "natural_lake_proximity",
        "flood_line_status",
        "blue_flood_line_distance",
        "red_flood_line_distance",
        "nallah_or_watercourse",
        "nallah_distance",
        "heritage_restriction",
        "defence_restriction",
    ),

    "building": (
        "project_type",
        "development_type",
        "existing_building",
        "building_use",
        "occupancy",
        "mixed_use",
        "requested_height",
        "requested_floors",
        "floor_height",
        "number_of_buildings",
        "group_housing",
    ),

    "units": (
        "requested_units",
        "requested_unit_mix",
        "unit_carpet_requirements",
        "minimum_units",
        "maximum_units",
        "unit_mix_preference",
        "requested_residential_area",
    ),

    "parking": (
        "tenement_carpet_areas",
        "parking_mode",
        "parking_preference",
        "parking_spaces_required",
        "visitor_parking_required",
        "two_wheeler_parking_required",
    ),

    "fire": (
        "sprinkler_system",
        "lift_required",
        "lift_count_preference",
        "staircase_count_preference",
        "refuge_area_preference",
    ),

    "services": (
        "water_supply_available",
        "sewerage_available",
    ),

    "design_preferences": (
        "building_orientation_preference",
        "maximize_fsi",
        "maximize_usable_area",
        "optimize_daylight",
        "optimize_ventilation",
    ),
}


def get_fields_for_group(
    group: str,
) -> tuple[str, ...]:

    return FIELD_GROUPS.get(
        group,
        (),
    )


# ==============================================================
# DEBUG / REPORTING
# ==============================================================

def describe_requirements() -> list[dict[str, Any]]:

    return [
        requirement_to_dict(item)
        for item in ALL_UDCPR_DESIGN_INPUTS
    ]


def print_requirement_summary() -> None:

    print("=" * 100)
    print("UDCPR DESIGN INPUT REQUIREMENTS")
    print("=" * 100)

    print(
        f"Total registered inputs : "
        f"{len(ALL_UDCPR_DESIGN_INPUTS)}"
    )

    print(
        f"Image-extractable       : "
        f"{len(IMAGE_EXTRACTABLE_FIELDS)}"
    )

    print(
        f"Validation fields       : "
        f"{len(DESIGN_VALIDATION_FIELDS)}"
    )

    print()

    for category in sorted(
        {
            item.category
            for item in ALL_UDCPR_DESIGN_INPUTS
        }
    ):

        requirements = get_requirements_for_category(
            category
        )

        print(
            f"{category:30} : "
            f"{len(requirements)}"
        )


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":

    print_requirement_summary()