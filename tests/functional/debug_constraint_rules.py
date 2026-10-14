from __future__ import annotations

import json

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.modules.planning.fact_context import PlanningFactContext
from townplanning.modules.planning.services.planning_service import PlanningService


context = PlanningFactContext(
    plot_area=745.6,
    plot_number="78/5",

    road_width=18.0,
    road_widths=[18.0],
    road_frontage_count=1,
    road_locations=["south"],

    building_type="Residential",
    building_use="residential",
    zone_type="Residential",

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

    maximize_fsi=True,
)

facts = context.to_planning_facts()

service = PlanningService()

constraints = service.evaluate(facts)

print("=" * 100)
print("APPLICABLE RULE RESULT JSON")
print("=" * 100)

for rule in constraints.applied_rules:

    category = str(
        getattr(rule, "category", "")
    ).lower()

    name = str(
        getattr(rule, "name", "")
    ).lower()

    interesting = (
        "fsi" in category
        or "fsi" in name
        or "tdr" in category
        or "tdr" in name
        or "incentive" in category
        or "incentive" in name
        or "setback" in category
        or "setback" in name
        or "margin" in category
        or "margin" in name
        or "height" in category
        or "height" in name
        or "storey" in category
        or "storey" in name
        or "floor" in category
        or "floor" in name
        or "coverage" in category
        or "coverage" in name
        or "parking" in category
        or "parking" in name
    )

    if not interesting:
        continue

    print()
    print("-" * 100)
    print("RULE ID  :", rule.rule_id)
    print("CATEGORY :", rule.category)
    print("NAME     :", rule.name)
    print("STATUS   :", rule.status)

    print("CONDITION:")
    print(
        json.dumps(
            rule.condition,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    print("RESULT:")
    print(
        json.dumps(
            rule.result,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

print()
print("=" * 100)
print("FINAL CONSTRAINTS")
print("=" * 100)

fields = [
    "basic_fsi",
    "premium_fsi",
    "tdr_fsi",
    "incentive_fsi",
    "maximum_fsi",
    "total_fsi",
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

for field in fields:
    print(
        f"{field:35} = "
        f"{getattr(constraints, field, None)!r}"
    )
