from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.planning.services.planning_input_gate import (
    PlanningInputGate,
)

from townplanning.modules.planning.services.planning_user_input_resolver import (
    PlanningUserInputResolver,
)


def main():

    print()
    print("=" * 100)
    print("PLANNING USER INPUT RESOLVER")
    print("=" * 100)

    facts = PlanningFacts(
        project_type="Residential Apartment",
        development_type="New Construction",
        plot_area=745.6,
        plot_number="78/5",

        north_direction=0.0,

        road_widths=[],
        road_frontage_count=0,
        road_locations=[],

        building_type="Residential Apartment",
        building_use="residential",

        redevelopment=False,
        existing_building=False,

        requested_units=6,

        maximize_fsi=True,
        maximize_parking=True,
        maximize_usable_area=True,
        optimize_daylight=True,
        optimize_ventilation=True,
    )

    gate = PlanningInputGate()

    #
    # Simulate the current missing information.
    #

    gate_result = gate.evaluate(
        facts
    )

    print()
    print("MISSING BEFORE USER INPUT")
    print("-" * 100)

    for item in gate_result.missing:

        print(
            item.field,
            "|",
            item.question,
        )

    #
    # User answers ONLY missing information.
    #

    user_input = (
        "18 m road. "
        "Road is on the south side. "
        "Yes, vehicular access is available. "
        
    )

    resolver = PlanningUserInputResolver()

    resolver.apply(
        facts,
        gate_result.missing,
        user_input,
    )

    print()
    print("FACTS AFTER USER INPUT")
    print("-" * 100)

    print(
        "plot_area:",
        facts.plot_area,
    )

    print(
        "plot_number:",
        facts.plot_number,
    )

    print(
        "road_width:",
        facts.road_width,
    )

    print(
        "road_widths:",
        facts.road_widths,
    )

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

    print(
        "zone:",
        facts.zone,
    )

    print(
        "reservation_present:",
        facts.reservation_present,
    )

    #
    # Re-run gate.
    #

    second_gate = gate.evaluate(
        facts
    )

    print()
    print("GATE AFTER USER INPUT")
    print("-" * 100)

    print(
        "READY:",
        second_gate.ready,
    )

    if second_gate.missing:

        print()
        print("STILL MISSING:")

        for item in second_gate.missing:

            print(
                item.field,
                "|",
                item.question,
            )

    else:

        print()
        print(
            "NO MANDATORY INFORMATION MISSING."
        )

    #
    # Assertions
    #

    assert facts.plot_area == 745.6
    assert facts.plot_number == "78/5"

    assert facts.road_width == 18.0
    assert facts.road_widths == [18.0]

    assert facts.road_frontage_count == 1
    assert facts.road_locations == ["south"]

    assert facts.access_available is True

    assert facts.zone is None
    assert facts.reservation_present is None
    assert second_gate.ready is False
    assert any(
    item.field == "plot_geometry"
    for item in second_gate.missing
)

    print()
    print("=" * 100)
    print(
        "PLANNING USER INPUT RESOLVER PASSED"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()
