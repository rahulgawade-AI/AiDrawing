from __future__ import annotations

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)
from townplanning.modules.planning.services.planning_input_flow import (
    PlanningInputFlow,
)


def main():

    print()
    print("=" * 100)
    print("PLANNING INPUT FLOW")
    print("=" * 100)

    facts = PlanningFacts(
        project_type="Residential Apartment",
        development_type="New Construction",
        plot_area=745.6,
        plot_number="78/5",
        building_type="Residential Apartment",
        building_use="residential",
        requested_units=6,
        road_widths=[],
        road_frontage_count=0,
        road_locations=[],
        access_available=None,
        zone=None,
        reservation_present=None,
    )

    flow = PlanningInputFlow()

    # ------------------------------------------------------
    # FIRST GATE
    # ------------------------------------------------------

    result = flow.evaluate(facts)

    print()
    print("FIRST GATE")
    print("-" * 100)
    print("READY:", result.gate.ready)

    for item in result.gate.missing:
        print(
            f"{item.field} | "
            f"{item.question}"
        )

    assert not result.gate.ready

    # ------------------------------------------------------
    # USER ANSWERS
    # ------------------------------------------------------

    user_answers = {
        "road_width": 18.0,
        "road_frontage": "south",
        "access_available": True,
        "zone": "Residential",
        "reservation_present": False,
    }

    result = flow.apply_user_input(
        facts,
        result.gate,
        user_answers,
    )

    # ------------------------------------------------------
    # FACTS
    # ------------------------------------------------------

    print()
    print("FACTS AFTER USER INPUT")
    print("-" * 100)

    print("plot_area:", facts.plot_area)
    print("plot_number:", facts.plot_number)
    print("road_width:", facts.road_width)
    print("road_widths:", facts.road_widths)
    print(
        "road_frontage_count:",
        facts.road_frontage_count,
    )
    print(
        "road_locations:",
        facts.road_locations,
    )
    print(
        "access_available:",
        facts.access_available,
    )
    print("zone:", facts.zone)
    print(
        "reservation_present:",
        facts.reservation_present,
    )

    # ------------------------------------------------------
    # SECOND GATE
    # ------------------------------------------------------

    print()
    print("SECOND GATE")
    print("-" * 100)
    print("READY:", result.gate.ready)

    if result.gate.missing:

        print()
        print("STILL MISSING:")

        for item in result.gate.missing:
            print(
                f"{item.field} | "
                f"{item.question}"
            )

    # ------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------

    assert facts.plot_area == 745.6
    assert facts.plot_number == "78/5"

    assert facts.road_width == 18.0
    assert facts.road_widths == [18.0]

    assert facts.road_frontage_count == 1
    assert facts.road_locations == ["south"]

    assert facts.access_available is True

    assert facts.zone == "Residential"
    assert facts.reservation_present is False

    assert result.gate.ready is True
    assert not result.gate.missing

    print()
    print("=" * 100)
    print("PLANNING INPUT FLOW PASSED")
    print("=" * 100)


if __name__ == "__main__":
    main()