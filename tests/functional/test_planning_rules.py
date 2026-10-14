from townplanning.modules.planning.fact_context import (
    PlanningFactContext,
)

from townplanning.modules.planning.services.planning_service import (
    PlanningService,
)


# ==============================================================
# TEST INPUT
# ==============================================================

context = PlanningFactContext(

    # ----------------------------------------------------------
    # SITE
    # ----------------------------------------------------------

    plot_area=745.6,

    plot_number="78/5",


    # ----------------------------------------------------------
    # ROAD
    # ----------------------------------------------------------

    road_width=18.0,

    road_widths=[
        18.0,
    ],

    road_frontage_count=1,

    road_locations=[
        "south",
    ],


    # ----------------------------------------------------------
    # BUILDING
    # ----------------------------------------------------------

    building_type="Residential",

    building_use="residential",


    # ----------------------------------------------------------
    # ZONE
    # ----------------------------------------------------------

    # Required by the current Basic FSI rule.

    zone_type="Residential",


    # ----------------------------------------------------------
    # RESIDENTIAL UNIT MIX
    # ----------------------------------------------------------

    # Used by persisted UDCPR Table No.8-B.

    requested_units=6,

    requested_unit_mix=[

        {
            "bhk": "2BHK",
            "units": 4,
            "carpet_area": 90,
        },

        {
            "bhk": "3BHK",
            "units": 2,
            "carpet_area": 125,
        },

    ],


    # ----------------------------------------------------------
    # OBJECTIVE
    # ----------------------------------------------------------

    maximize_fsi=True,

    maximize_parking=True,

)


# ==============================================================
# NORMALIZE / CONVERT FACTS
# ==============================================================

facts = context.to_planning_facts()


print()
print("=" * 80)
print("NORMALIZED PLANNING FACTS")
print("=" * 80)

print(
    "building_type :",
    facts.building_type,
)

print(
    "building_use  :",
    facts.building_use,
)

print(
    "zone_type     :",
    facts.zone_type,
)

print(
    "plot_area     :",
    facts.plot_area,
)

print(
    "road_width    :",
    facts.road_width,
)

print(
    "road_locations:",
    facts.road_locations,
)

print(
    "requested_units:",
    facts.requested_units,
)

print(
    "requested_unit_mix:",
    facts.requested_unit_mix,
)


# ==============================================================
# RUN PLANNING ENGINE
# ==============================================================

service = PlanningService()


try:

    constraints = service.evaluate(
        facts
    )


    # ==========================================================
    # FINAL PLANNING RESULT
    # ==========================================================

    print()
    print("=" * 80)
    print("FINAL PLANNING RESULT")
    print("=" * 80)

    print(
        "basic_fsi                =",
        constraints.basic_fsi,
    )

    print(
        "premium_fsi              =",
        constraints.premium_fsi,
    )

    print(
        "tdr_fsi                  =",
        constraints.tdr_fsi,
    )

    print(
        "incentive_fsi            =",
        constraints.incentive_fsi,
    )

    print(
        "maximum_fsi              =",
        constraints.maximum_fsi,
    )

    print(
        "total_fsi                =",
        constraints.total_fsi,
    )

    print(
        "maximum_built_up_area    =",
        constraints.maximum_built_up_area,
    )

    print(
        "maximum_ground_coverage  =",
        constraints.maximum_ground_coverage,
    )

    print(
        "front_setback            =",
        constraints.front_setback,
    )

    print(
        "rear_setback             =",
        constraints.rear_setback,
    )

    print(
        "side_setback_left        =",
        constraints.side_setback_left,
    )

    print(
        "side_setback_right       =",
        constraints.side_setback_right,
    )

    print(
        "maximum_height_m         =",
        constraints.maximum_height_m,
    )

    print(
        "maximum_storeys          =",
        constraints.maximum_storeys,
    )

    print(
        "car_parking_required     =",
        constraints.car_parking_required,
    )

    print(
        "two_wheeler_parking_req  =",
        constraints.two_wheeler_parking_required,
    )

    print(
        "visitor_parking_required =",
        constraints.visitor_parking_required,
    )

    print(
        "parking_area_required    =",
        constraints.parking_area_required,
    )


    # ==========================================================
    # TABLE-DRIVEN PARKING
    # ==========================================================

    print()
    print("=" * 80)
    print("TABLE-DRIVEN PARKING")
    print("=" * 80)

    parking_result = (
        constraints.metadata.get(
            "parking_table_result"
        )
    )

    if parking_result:

        print(
            "STATUS :",
            parking_result.get(
                "status"
            ),
        )

        source = constraints.metadata.get(
            "parking_table_source",
            {},
        )

        print(
            "TABLE  :",
            parking_result.get(
                "table"
            ),
        )

        print(
            "PAGE   :",
            parking_result.get(
                "page"
            ),
        )

        print(
            "INDEX  :",
            parking_result.get(
                "table_index"
            ),
        )

        print(
            "TABLE ID:",
            parking_result.get(
                "table_id"
            ),
        )

        print(
            "CAR    :",
            parking_result.get(
                "car_parking_required"
            ),
        )

        print(
            "TWO-WHEELER:",
            parking_result.get(
                "two_wheeler_parking_required"
            ),
        )

        print(
            "VISITOR:",
            parking_result.get(
                "visitor_parking_required"
            ),
        )

    else:

        print(
            "parking_table_result : NOT AVAILABLE"
        )


    # ==========================================================
    # DERIVED REGULATORY FACTS
    # ==========================================================

    print()
    print("=" * 80)
    print("DERIVED REGULATORY FACTS")
    print("=" * 80)

    derived = constraints.metadata.get(
        "derived_regulatory_facts",
        {},
    )

    for key, value in derived.items():

        print(
            f"{key:45} = {value}"
        )


    print()
    print(
        "evaluation_passes =",
        constraints.metadata.get(
            "evaluation_passes"
        ),
    )


    # ==========================================================
    # APPLIED RULES
    # ==========================================================

    print()
    print("=" * 80)
    print("APPLIED RULES")
    print("=" * 80)

    print(
        "COUNT:",
        len(
            constraints.applied_rules
        ),
    )

    for rule in constraints.applied_rules:

        print()
        print(
            "[APPLIED]",
            rule.category,
            "|",
            rule.name,
        )

        print(
            "  rule_id  :",
            rule.rule_id,
        )

        print(
            "  condition:",
            rule.condition,
        )

        print(
            "  result   :",
            rule.result,
        )

        print(
            "  reason   :",
            rule.reason,
        )


    # ==========================================================
    # UNRESOLVED RULES
    # ==========================================================

    print()
    print("=" * 80)
    print("UNRESOLVED RULES")
    print("=" * 80)

    print(
        "COUNT:",
        len(
            constraints.unresolved_rules
        ),
    )

    for rule in constraints.unresolved_rules:

        print()
        print(
            "[UNRESOLVED]",
            rule.category,
            "|",
            rule.name,
        )

        print(
            "  rule_id  :",
            rule.rule_id,
        )

        print(
            "  condition:",
            rule.condition,
        )

        print(
            "  result   :",
            rule.result,
        )

        print(
            "  reason   :",
            rule.reason,
        )


    # ==========================================================
    # REJECTED / NOT APPLICABLE RULES
    # ==========================================================

    print()
    print("=" * 80)
    print("REJECTED / NOT APPLICABLE RULES")
    print("=" * 80)

    print(
        "COUNT:",
        len(
            constraints.rejected_rules
        ),
    )

    for rule in constraints.rejected_rules:

        print()
        print(
            "[REJECTED]",
            rule.category,
            "|",
            rule.name,
            "| status=",
            rule.status,
        )

        print(
            "  rule_id:",
            rule.rule_id,
        )

        print(
            "  condition:",
            rule.condition,
        )

        print(
            "  reason:",
            rule.reason,
        )


    # ==========================================================
    # BASIC SANITY CHECKS
    # ==========================================================

    print()
    print("=" * 80)
    print("SANITY CHECKS")
    print("=" * 80)


    assert facts.plot_area == 745.6

    assert facts.road_width == 18.0

    assert facts.building_use == "residential"

    assert facts.zone_type == "Residential"


    # Existing FSI behaviour

    assert constraints.basic_fsi == 1.0

    assert constraints.premium_fsi == 2.0

    assert constraints.maximum_fsi == 3.0

    assert constraints.total_fsi == 3.0

    assert constraints.maximum_built_up_area == 2236.8


    # Table 8-B behaviour

    assert (
        constraints.car_parking_required
        == 6
    )

    assert (
        constraints.two_wheeler_parking_required
        == 6
    )

    assert (
        constraints.visitor_parking_required
        == 1
    )


    parking_result = (
        constraints.metadata.get(
            "parking_table_result"
        )
    )

    assert (
        parking_result is not None
    )

    assert (
        parking_result.get(
            "status"
        )
        == "calculated"
    )


    print()
    print("=" * 80)
    print("PLANNING RULE TEST PASSED")
    print("=" * 80)


finally:

    # PlanningService owns the table DB session.

    if hasattr(
        service,
        "close",
    ):
        service.close()

print()
print("=" * 80)
print("CONSTRAINT COMPLETENESS")
print("=" * 80)

constraint_fields = [
    "basic_fsi",
    "premium_fsi",
    "tdr_fsi",
    "incentive_fsi",
    "maximum_fsi",
    "total_fsi",
    "maximum_built_up_area",
    "maximum_ground_coverage",
    "front_setback",
    "rear_setback",
    "side_setback_left",
    "side_setback_right",
    "maximum_height_m",
    "maximum_storeys",
    "car_parking_required",
    "two_wheeler_parking_required",
    "visitor_parking_required",
    "parking_area_required",
]

for field in constraint_fields:

    value = getattr(
        constraints,
        field,
        None,
    )

    status = (
        "RESOLVED"
        if value is not None
        else "UNRESOLVED"
    )

    print(
        f"{field:35} = "
        f"{value!r:15} [{status}]"
    )