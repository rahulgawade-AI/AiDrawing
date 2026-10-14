from __future__ import annotations

from townplanning.modules.building.services.building_design_service import (
    BuildingDesignService,
)
from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)


def main():

    print()
    print("=" * 100)
    print("PLANNING → DETERMINISTIC RULES → BUILDING DESIGN")
    print("=" * 100)

    facts = PlanningFacts(
        project_type="Residential Apartment",
        development_type="New Construction",

        plot_area=745.6,
        plot_number="78/5",

        building_type="Residential Apartment",
        building_use="residential",

        requested_units=6,

        road_width=18.0,
        road_widths=[18.0],

        road_frontage_count=1,
        road_locations=["south"],

        access_available=True,

        zone="Residential",
        reservation_present=False,
    )

    service = BuildingDesignService()

    try:

        # ======================================================
        # 1. DETERMINISTIC PLANNING
        # ======================================================

        print()
        print(
            "[1] RUNNING DETERMINISTIC PLANNING..."
        )
        print("-" * 100)

        result = service.generate(
            facts
        )

        constraints = result.constraints

        print(
            "APPLIED RULES:",
            len(
                constraints.applied_rules
            ),
        )

        print(
            "UNRESOLVED RULES:",
            len(
                constraints.unresolved_rules
            ),
        )

        print(
            "REJECTED RULES:",
            len(
                constraints.rejected_rules
            ),
        )

        # ======================================================
        # 2. PLANNING CONSTRAINTS
        # ======================================================

        print()
        print(
            "PLANNING CONSTRAINTS"
        )
        print("-" * 100)

        constraint_fields = (
            "basic_fsi",
            "maximum_fsi",
            "maximum_built_up_area",
            "maximum_ground_coverage",
            "front_setback",
            "rear_setback",
            "side_setback_left",
            "side_setback_right",
            "maximum_height_m",
            "maximum_storeys",
            "car_parking_required",
        )

        for name in constraint_fields:

            print(
                f"{name}:",
                getattr(
                    constraints,
                    name,
                    None,
                ),
            )

        # ======================================================
        # 3. BUILDING DESIGN PLAN
        # ======================================================

        print()
        print("=" * 100)
        print(
            "BUILDING DESIGN PLAN"
        )
        print("=" * 100)

        plan = result.design_plan

        # IMPORTANT:
        # BuildingDesignPlan is a flat dataclass.
        # It does NOT contain facts or constraints.

        print(
            "plot_area_m2:",
            plan.plot_area_m2,
        )

        print(
            "maximum_fsi:",
            plan.maximum_fsi,
        )

        print(
            "maximum_built_up_area_m2:",
            plan.maximum_built_up_area_m2,
        )

        print(
            "maximum_ground_coverage_m2:",
            plan.maximum_ground_coverage_m2,
        )

        print(
            "front_setback_m:",
            plan.front_setback_m,
        )

        print(
            "rear_setback_m:",
            plan.rear_setback_m,
        )

        print(
            "side_setback_left_m:",
            plan.side_setback_left_m,
        )

        print(
            "side_setback_right_m:",
            plan.side_setback_right_m,
        )

        print(
            "minimum_open_space_m2:",
            plan.minimum_open_space_m2,
        )

        print(
            "maximum_height_m:",
            plan.maximum_height_m,
        )

        print(
            "maximum_storeys:",
            plan.maximum_storeys,
        )

        print(
            "car_parking_required:",
            plan.car_parking_required,
        )

        print(
            "parking_area_required_m2:",
            plan.parking_area_required_m2,
        )

        print(
            "staircase_count:",
            plan.staircase_count,
        )

        print(
            "lift_required:",
            plan.lift_required,
        )

        # ======================================================
        # 4. DESIGN PLAN METADATA
        # ======================================================

        print()
        print(
            "DESIGN PLAN METADATA"
        )
        print("-" * 100)

        for key, value in plan.metadata.items():

            print(
                f"{key}: {value}"
            )

        # ======================================================
        # 5. VALIDATION
        # ======================================================

        print()
        print("=" * 100)
        print(
            "VALIDATION"
        )
        print("=" * 100)

        # Planning facts remain on the result.
        assert (
            result.facts is facts
        )

        assert (
            result.facts.plot_area
            == 745.6
        )

        assert (
            result.facts.plot_number
            == "78/5"
        )

        assert (
            result.facts.road_width
            == 18.0
        )

        assert (
            result.facts.road_widths
            == [18.0]
        )

        assert (
            result.facts.road_frontage_count
            == 1
        )

        assert (
            result.facts.road_locations
            == ["south"]
        )

        assert (
            result.facts.access_available
            is True
        )

        assert (
            result.facts.zone
            == "Residential"
        )

        assert (
            result.facts.reservation_present
            is False
        )

        # Planning constraints remain on the result.
        assert (
            result.constraints
            is constraints
        )

        # BuildingDesignPlan receives the deterministic
        # values from PlanningFacts / PlanningConstraints.
        assert (
            plan.plot_area_m2
            == 745.6
        )

        assert (
            plan.maximum_fsi
            == constraints.maximum_fsi
        )

        assert (
            plan.maximum_built_up_area_m2
            == constraints.maximum_built_up_area
        )

        assert (
            plan.maximum_ground_coverage_m2
            == constraints.maximum_ground_coverage
        )

        assert (
            plan.front_setback_m
            == constraints.front_setback
        )

        assert (
            plan.rear_setback_m
            == constraints.rear_setback
        )

        assert (
            plan.side_setback_left_m
            == constraints.side_setback_left
        )

        assert (
            plan.side_setback_right_m
            == constraints.side_setback_right
        )

        assert (
            plan.minimum_open_space_m2
            == constraints.minimum_open_space
        )

        assert (
            plan.maximum_height_m
            == constraints.maximum_height_m
        )

        assert (
            plan.maximum_storeys
            == constraints.maximum_storeys
        )

        assert (
            plan.car_parking_required
            == constraints.car_parking_required
        )

        assert (
            plan.parking_area_required_m2
            == constraints.parking_area_required
        )

        assert (
            plan.fire_access_required
            == constraints.fire_access_required
        )

        assert (
            plan.fire_lift_required
            == constraints.fire_lift_required
        )

        assert (
            plan.fire_staircase_required
            == constraints.fire_staircase_required
        )

        assert (
            plan.minimum_exit_count
            == constraints.minimum_exit_count
        )

        assert (
            plan.minimum_exit_width_m
            == constraints.minimum_exit_width_m
        )

        assert (
            plan.staircase_count
            == constraints.staircase_count
        )

        assert (
            plan.staircase_width_m
            == constraints.staircase_width_m
        )

        assert (
            plan.corridor_width_m
            == constraints.corridor_width_m
        )

        assert (
            plan.lift_required
            == constraints.lift_required
        )

        assert (
            plan.lift_count
            == constraints.lift_count
        )

        assert (
            plan.accessible_entrance_required
            == constraints.accessible_entrance_required
        )

        assert (
            plan.ramp_required
            == constraints.ramp_required
        )

        assert (
            plan.ramp_width_m
            == constraints.ramp_width_m
        )

        assert (
            plan.ramp_gradient
            == constraints.ramp_gradient
        )

        assert (
            plan.recreational_open_space_m2
            == constraints.recreational_open_space_m2
        )

        assert (
            plan.amenity_space_m2
            == constraints.amenity_space_m2
        )

        assert (
            plan.road_widening
            == constraints.road_widening
        )

        assert (
            plan.reservation_present
            == constraints.reservation_present
        )

        print(
            "✓ PlanningFacts preserved"
        )

        print(
            "✓ Deterministic PlanningService executed"
        )

        print(
            "✓ PlanningConstraints produced"
        )

        print(
            "✓ BuildingDesignPlan generated"
        )

        print(
            "✓ Planning values transferred to design envelope"
        )

        print()
        print("=" * 100)
        print(
            "PLANNING → BUILDING DESIGN PASSED"
        )
        print("=" * 100)

    finally:

        service.close()


if __name__ == "__main__":
    main()
