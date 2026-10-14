from __future__ import annotations

from pathlib import Path

from townplanning.modules.vision.services.vision_service import (
    VisionService,
)

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.planning.services.planning_input_flow import (
    PlanningInputFlow,
)

from townplanning.modules.planning.services.vision_planning_facts_adapter import (
    VisionPlanningFactsAdapter,
)


TEST_IMAGE = (
    Path(__file__).parent
    / "data"
    / "sample2.png"
)


def test_vision_end_to_end():

    print()
    print("=" * 100)
    print("VISION → PLANNING INTEGRATION TEST")
    print("=" * 100)

    # =========================================================
    # 1. LOAD DRAWING
    # =========================================================

    print()
    print("[1] Loading drawing...")

    assert TEST_IMAGE.exists(), (
        f"Test image not found: {TEST_IMAGE}"
    )

    print(
        f"    ✓ Image: {TEST_IMAGE}"
    )

    # =========================================================
    # 2. RUN COMPLETE VISION PIPELINE
    # =========================================================

    print()
    print("[2] Running VisionService...")

    vision = VisionService()

    spatial_context = vision.process(
        TEST_IMAGE
    )

    assert spatial_context is not None

    print()
    print(
        "    ✓ SpatialContext generated"
    )

    # =========================================================
    # 3. DISPLAY VISION RESULTS
    # =========================================================

    print()
    print("=" * 100)
    print("VISION RESULTS")
    print("=" * 100)

    print(
        f"    Plot boundary : "
        f"{spatial_context.boundary}"
    )

    print(
        f"    Plot area     : "
        f"{spatial_context.area}"
    )

    print(
        f"    Plot number   : "
        f"{spatial_context.plot_number}"
    )

    print(
        f"    Dimensions    : "
        f"{len(spatial_context.dimensions)}"
    )

    print(
        f"    OCR texts     : "
        f"{len(spatial_context.texts)}"
    )

    print(
        f"    Roads         : "
        f"{len(spatial_context.roads)}"
    )

    print(
        f"    North         : "
        f"{spatial_context.north}"
    )

    print(
        f"    Scale         : "
        f"{spatial_context.scale}"
    )

    print(
        f"    Boundary edges: "
        f"{len(spatial_context.edges)}"
    )

    print(
        f"    Edge dimensions: "
        f"{len(spatial_context.edge_dimensions)}"
    )

    print(
        f"    Edge roads    : "
        f"{len(spatial_context.edge_roads)}"
    )

    # =========================================================
    # 4. CONVERT VISION → PLANNING FACTS
    # =========================================================

    print()
    print("=" * 100)
    print("VISION → PLANNING FACTS")
    print("=" * 100)

    facts = VisionPlanningFactsAdapter.convert(
        spatial_context
    )

    assert isinstance(
        facts,
        PlanningFacts,
    )

    print(
        "    ✓ SpatialContext converted to PlanningFacts"
    )

    # =========================================================
    # 5. DISPLAY EXTRACTED PLANNING FACTS
    # =========================================================

    print()
    print("=" * 100)
    print("EXTRACTED PLANNING FACTS")
    print("=" * 100)

    facts_dict = facts.to_dict()

    for field_name, value in facts_dict.items():

        # The values dictionary contains large/internal
        # Vision objects, so display it separately below.
        if field_name == "values":
            continue

        print(
            f"    {field_name}: {value}"
        )

    # =========================================================
    # 6. DISPLAY VISION FACT PROVENANCE
    # =========================================================

    print()
    print("=" * 100)
    print("VISION FACT PROVENANCE")
    print("=" * 100)

    if facts.fact_sources:

        for field_name, source in (
            facts.fact_sources.items()
        ):

            confidence = facts.fact_confidence.get(
                field_name
            )

            print(
                f"    {field_name}"
                f" -> source={source}"
                f" confidence={confidence}"
            )

    else:

        print(
            "    No fact provenance recorded."
        )

    # =========================================================
    # 7. DISPLAY IMPORTANT VISION VALUES
    # =========================================================

    print()
    print("=" * 100)
    print("VISION-DERIVED VALUES")
    print("=" * 100)

    detected_roads = facts.values.get(
        "detected_roads"
    )

    if detected_roads:

        print()
        print("    Detected roads:")

        for index, road in enumerate(
            detected_roads,
            start=1,
        ):

            print(
                f"        {index}. {road}"
            )

    else:

        print(
            "    Detected roads: none"
        )

    detected_dimensions = facts.values.get(
        "detected_dimensions"
    )

    if detected_dimensions:

        print()
        print("    Detected dimensions:")

        for index, dimension in enumerate(
            detected_dimensions,
            start=1,
        ):

            print(
                f"        {index}. {dimension}"
            )

    else:

        print(
            "    Detected dimensions: none"
        )

    drawing_scale = facts.values.get(
        "drawing_scale"
    )

    print(
        f"    Drawing scale: {drawing_scale}"
    )

    # =========================================================
    # 8. RUN EXISTING PLANNING INPUT FLOW
    # =========================================================

    print()
    print("=" * 100)
    print("PLANNING INPUT FLOW")
    print("=" * 100)

    planning_flow = PlanningInputFlow()

    result = planning_flow.evaluate(
        facts
    )

    assert result is not None

    assert result.facts is facts

    assert result.gate is not None

    print(
        "    ✓ PlanningInputFlow evaluated"
    )

    # =========================================================
    # 9. PLANNING INPUT GATE RESULT
    # =========================================================

    print()
    print("=" * 100)
    print("PLANNING INPUT GATE RESULT")
    print("=" * 100)

    gate = result.gate

    print(
        f"    Gate result: {gate}"
    )

    # =========================================================
    # 10. MISSING INFORMATION
    # =========================================================

    print()
    print("=" * 100)
    print("MISSING PLANNING INFORMATION")
    print("=" * 100)

    missing = getattr(
        gate,
        "missing",
        None,
    )

    if missing is None:

        missing = getattr(
            gate,
            "missing_information",
            [],
        )

    if missing:

        for index, item in enumerate(
            missing,
            start=1,
        ):

            print(
                f"    {index}. {item}"
            )

    else:

        print(
            "    ✓ No missing information"
        )

    # =========================================================
    # 11. FINAL ASSERTIONS
    # =========================================================

    assert isinstance(
        spatial_context.roads,
        list,
    )

    assert isinstance(
        spatial_context.dimensions,
        list,
    )

    assert isinstance(
        facts,
        PlanningFacts,
    )

    assert result.facts is facts

    # =========================================================
    # 12. COMPLETE
    # =========================================================

    print()
    print("=" * 100)
    print("VISION → PLANNING INTEGRATION PASSED")
    print("=" * 100)