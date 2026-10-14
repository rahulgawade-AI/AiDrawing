from pathlib import Path

from townplanning.modules.vision.services.vision_service import (
    VisionService,
)

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)


TEST_IMAGE = (
    Path(__file__).parent
    / "data"
    / "sample1.png"
)


def main():

    print()
    print("=" * 100)
    print("VISION → PLANNING FACTS INTEGRATION TEST")
    print("=" * 100)

    # ==========================================================
    # VISION
    # ==========================================================

    print()
    print("[1] Running VisionService...")
    print()

    vision = VisionService()

    spatial_context = vision.process(
        TEST_IMAGE
    )

    print()
    print("VISION OUTPUT")
    print("-" * 100)

    print(
        "Plot area:",
        spatial_context.area,
    )

    print(
        "Plot number:",
        spatial_context.plot_number,
    )

    print(
        "Road count:",
        len(
            spatial_context.roads
        ),
    )

    for index, road in enumerate(
        spatial_context.roads,
        start=1,
    ):

        print(
            f"Road {index}:",
            road,
        )

    print(
        "North:",
        spatial_context.north,
    )

    print(
        "Scale:",
        spatial_context.scale,
    )

    print(
        "Dimensions:",
        len(
            spatial_context.dimensions
        ),
    )

    print(
        "OCR text blocks:",
        len(
            spatial_context.texts
        ),
    )

    # ==========================================================
    # USER REQUIREMENTS
    #
    # Simulates the text supplied by the user.
    # This will later come from the application/API.
    # ==========================================================

    user_requirements = {

        "project_type":
            "Residential Apartment",

        "development_type":
            "New Construction",

        "building_type":
            "Residential Apartment",

        "building_use":
            "residential",

        "requested_units":
            6,
    }

    # ==========================================================
    # VISION → PLANNING FACTS
    # ==========================================================

    print()
    print(
        "[2] Converting SpatialContext → PlanningFacts..."
    )

    facts = (
        PlanningFacts.from_spatial_context(
            spatial_context,
            user_requirements=user_requirements,
        )
    )

    facts.normalize()

    # ==========================================================
    # CANONICAL FACTS
    # ==========================================================

    print()
    print("CANONICAL PLANNING FACTS")
    print("-" * 100)

    data = facts.to_dict()

    for key, value in data.items():

        print(
            f"{key}: {value}"
        )

    # ==========================================================
    # REQUIRED ASSERTIONS
    # ==========================================================

    print()
    print("VALIDATION")
    print("-" * 100)

    assert (
        facts.project_type
        == "Residential Apartment"
    )

    assert (
        facts.building_type
        == "Residential Apartment"
    )

    assert (
        facts.building_use
        == "residential"
    )

    assert (
        facts.development_type
        == "New Construction"
    )

    assert (
        facts.requested_units
        == 6
    )

    assert isinstance(
        facts.road_widths,
        list,
    )

    assert isinstance(
        facts.road_locations,
        list,
    )

    assert isinstance(
        facts.values.get(
            "vision_text",
            [],
        ),
        list,
    )

    assert isinstance(
        facts.values.get(
            "vision_dimensions",
            [],
        ),
        list,
    )

    print(
        "✓ User requirements preserved"
    )

    print(
        "✓ Vision text preserved"
    )

    print(
        "✓ Vision dimensions preserved"
    )

    print(
        "✓ Road facts mapped"
    )

    print(
        "✓ PlanningFacts normalization passed"
    )

    print()
    print("=" * 100)
    print(
        "VISION → PLANNING FACTS PASSED"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()
