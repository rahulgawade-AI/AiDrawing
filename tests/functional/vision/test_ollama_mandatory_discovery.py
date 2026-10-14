from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.planning.mandatory.ollama_mandatory_discovery import (
    OllamaMandatoryDiscovery,
)


def main():

    # ==========================================================
    # CANONICAL TEST PROJECT
    #
    # This is ONLY test input.
    # No regulatory values are hard-coded here.
    # ==========================================================

    facts = PlanningFacts(

        # ------------------------------------------------------
        # LOCATION
        # ------------------------------------------------------

        state="Maharashtra",
        district="Pune",
        city="Pune",

        location_type="Urban",

        zone_type="Residential Zone - R-1",
        land_use_zone="Residential Zone - R-1",
        land_use_classification="Residential",

        # ------------------------------------------------------
        # AUTHORITY
        # ------------------------------------------------------

        planning_authority="Municipal Corporation",
        development_authority=None,
        municipality="Pune",

        # ------------------------------------------------------
        # PLOT
        # ------------------------------------------------------

        plot_area=745.6,

        # ------------------------------------------------------
        # ROAD
        # ------------------------------------------------------

        road_width=12.0,
        road_widths=[12.0],
        road_frontage_count=1,

        road_type=None,
        road_classification=None,

        access_available=True,

        # ------------------------------------------------------
        # LOCATION RESTRICTIONS
        # ------------------------------------------------------

        congested_area=False,

        tod_zone=False,
        heritage_zone=False,
        crz_zone=False,
        eco_sensitive_zone=False,
        airport_restriction=False,

        # ------------------------------------------------------
        # RESERVATION
        # ------------------------------------------------------

        reservation_present=False,
        reservation_type=None,

        # ------------------------------------------------------
        # BUILDING
        # ------------------------------------------------------

        project_type="Residential building",
        development_type="New construction",

        building_type="Residential building",
        building_use="residential",

        building_height=15.0,
        number_of_floors=5,

        mixed_use=False,
        group_housing=False,

        # ------------------------------------------------------
        # EXISTING / REDEVELOPMENT
        # ------------------------------------------------------

        redevelopment=False,
        rehabilitation=False,
        existing_building=False,

        # ------------------------------------------------------
        # HOUSING REQUIREMENT
        # ------------------------------------------------------

        requested_units=12,

        requested_1bhk_units=None,
        requested_2bhk_units=None,
        requested_3bhk_units=None,
        requested_unit_mix=None,

        # ------------------------------------------------------
        # AREA REQUIREMENTS
        # ------------------------------------------------------

        requested_commercial_area=None,
        requested_residential_area=None,

        # ------------------------------------------------------
        # PROPOSED DESIGN
        # ------------------------------------------------------

        requested_height=15.0,
        requested_floors=5,

        requested_fsi=None,

        # ------------------------------------------------------
        # DESIGN OBJECTIVES
        # ------------------------------------------------------

        maximize_fsi=True,
        maximize_parking=True,
        maximize_usable_area=True,

        optimize_daylight=True,
        optimize_ventilation=True,
    )

    # ==========================================================
    # SOURCE
    #
    # TEMPORARY TEST SOURCE ONLY.
    #
    # IMPORTANT:
    # This will be replaced by actual UDCPR PDF/Chroma
    # retrieval after the PlanningFacts test is confirmed.
    # ==========================================================

    source = """
UDCPR-2020

4.2 LAND USE CLASSIFICATION AND EQUIVALENCY OF ZONES

Residential Zone includes Residential Zone - R-1.

4.3 RESIDENTIAL ZONE - R-1

Residential Zone - R-1 is a residential land-use zone.

6.2.1
Marginal Distances and Set-back for Residential Buildings and
mixed use with Height up to 15.0 m. or as mentioned in Table No.6-D.

The provisions for minimum marginal distances as given in
Table No.6-D shall apply for the Residential buildings,
Residential with mixed uses permissible in Residential Zone
and Residential buildings permissible in other zones.

6.3
PERMISSIBLE FSI

Table 6-G:

Road width in meters:
12 m and above but below 15 m

Basic FSI:
1.00

FSI on payment of premium:
0.50

Maximum permissible TDR loading:
1.00

Maximum building potential on plot including in-situ FSI:
2.50

The applicable authority/table column must be determined from
the actual UDCPR table context and the supplied planning authority.
"""
    # ==========================================================
    # OLLAMA
    # ==========================================================

    engine = OllamaMandatoryDiscovery()

    result = engine.discover(
        facts=facts,
        regulation_text=source,
        source_reference="UDCPR-2020",
    )

    # ==========================================================
    # OUTPUT
    # ==========================================================

    print("=" * 100)
    print("OLLAMA MANDATORY DISCOVERY")
    print("=" * 100)

    print()
    print("PLANNING FACTS")
    print("-" * 100)

    fact_values = engine._serialize_facts(
        facts
    )

    for key, value in fact_values.items():
        print(
            f"{key:35}: {value}"
        )

    print()
    print("DISCOVERY RESULT")
    print("-" * 100)

    print(
        "CANDIDATE:",
        result.candidate,
    )

    print(
        "TITLE:",
        result.title,
    )

    print(
        "REGULATION:",
        result.regulation_number,
    )

    print(
        "CLAUSE:",
        result.clause,
    )

    print()
    print("REQUIRED FACTS:")

    if not result.required_facts:
        print(" NONE")

    for item in result.required_facts:
        print(
            " -",
            item,
        )

    print()
    print("CONDITIONS:")

    if not result.conditions:
        print(" NONE")

    for item in result.conditions:
        print(
            " -",
            item,
        )

    print()
    print("DETERMINISTIC CONSTRAINTS:")

    if not result.constraints:
        print(" NONE")

    for constraint in result.constraints:

        print(
            " -",
            constraint.field,
            "=",
            constraint.value,
            constraint.unit or "",
        )

        print(
            "   SOURCE:",
            constraint.source_text,
        )

        print(
            "   REF:",
            constraint.source_reference,
        )

    print()
    print("REASON:")
    print(
        result.reason
    )


if __name__ == "__main__":
    main()