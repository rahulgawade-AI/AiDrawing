from __future__ import annotations

from townplanning.modules.building.services.building_design_service import (
    BuildingDesignService,
)
from townplanning.modules.building.services.building_layout_generator import (
    BuildingLayoutGenerator,
)
from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)


def main():

    print()
    print("=" * 100)
    print("BUILDING DESIGN → LAYOUT ENVELOPE")
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

    design_service = BuildingDesignService()

    try:

        result = design_service.generate(
            facts
        )

        plan = result.design_plan

        print()
        print("BUILDING DESIGN PLAN")
        print("-" * 100)

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

        layout_generator = (
            BuildingLayoutGenerator()
        )

        layout = layout_generator.generate(
            facts,
            plan,
        )

        print()
        print("LAYOUT ENVELOPE")
        print("-" * 100)

        print(
            "feasible:",
            layout.feasible,
        )

        print(
            "reason:",
            layout.reason,
        )

        print(
            "plot_area_m2:",
            layout.plot_area_m2,
        )

        print(
            "maximum_built_up_area_m2:",
            layout.maximum_built_up_area_m2,
        )

        print(
            "maximum_ground_coverage_m2:",
            layout.maximum_ground_coverage_m2,
        )

        print(
            "buildable_area_m2:",
            layout.buildable_area_m2,
        )

        print()
        print("METADATA")
        print("-" * 100)

        for key, value in layout.metadata.items():

            print(
                f"{key}: {value}"
            )

        # --------------------------------------------------
        # Current repository state:
        #
        # maximum_ground_coverage_m2 is None.
        #
        # Therefore the generator MUST NOT invent a
        # footprint.
        # --------------------------------------------------

        assert layout.feasible is False

        assert (
            layout.plot_area_m2
            == 745.6
        )

        assert (
            layout.maximum_built_up_area_m2
            == 2236.8
        )

        assert (
            layout.maximum_ground_coverage_m2
            is None
        )

        assert (
            layout.buildable_area_m2
            is None
        )

        assert (
            layout.metadata["status"]
            == "CONSTRAINTS_INCOMPLETE"
        )

        print()
        print("=" * 100)
        print("BUILDING LAYOUT ENVELOPE TEST PASSED")
        print("=" * 100)

    finally:

        design_service.close()


if __name__ == "__main__":
    main()
