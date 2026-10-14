from pathlib import Path

from townplanning.modules.vision.services.vision_service import (
    VisionService,
)

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.planning.services.planning_service import (
    PlanningService,
)

from townplanning.modules.planning.services.planning_input_gate import (
    PlanningInputGate,
)


def main():

    print()
    print("=" * 100)
    print("VISION → PLANNING → INPUT GATE")
    print("=" * 100)

    #
    # ----------------------------------------------------------
    # 1. USER REQUIREMENTS
    # ----------------------------------------------------------
    #

    user_requirements = {
        "project_type": "Residential Apartment",
        "building_type": "Residential Apartment",
        "building_use": "residential",
        "development_type": "New Construction",
        "requested_units": 6,
    }

    #
    # ----------------------------------------------------------
    # 2. VISION
    # ----------------------------------------------------------
    #

    image_path = Path(
        "tests/functional/vision/data/sample1.png"
    )

    print()
    print("[1] Running VisionService...")

    vision = VisionService()

    spatial_context = vision.process(
        image_path
    )

    #
    # ----------------------------------------------------------
    # 3. VISION → PLANNING FACTS
    # ----------------------------------------------------------
    #

    print()
    print("[2] Converting SpatialContext → PlanningFacts...")

    facts = PlanningFacts.from_spatial_context(
        spatial_context=spatial_context,
        user_requirements=user_requirements,
    )

    print()
    print("CANONICAL FACTS")
    print("-" * 100)

    for key, value in facts.to_dict().items():
        print(
            f"{key}: {value}"
        )

    #
    # ----------------------------------------------------------
    # 4. DETERMINISTIC PLANNING
    # ----------------------------------------------------------
    #

    print()
    print("[3] Running deterministic PlanningService...")

    planning_service = PlanningService()

    constraints = planning_service.evaluate(
        facts
    )

    #
    # ----------------------------------------------------------
    # 5. APPLIED RULES
    # ----------------------------------------------------------
    #

    applied_rules = (
        constraints.applied_rules
    )

    print()
    print("APPLIED RULES")
    print("-" * 100)

    print(
        "COUNT:",
        len(applied_rules),
    )

    for rule in applied_rules:

        print(
            getattr(
                rule,
                "rule_id",
                "",
            ),
            "|",
            getattr(
                rule,
                "name",
                "",
            ),
        )

    #
    # ----------------------------------------------------------
    # 6. INPUT GATE
    # ----------------------------------------------------------
    #

    print()
    print("[4] Running PlanningInputGate...")

    gate = PlanningInputGate()

    gate_result = gate.evaluate(
        facts=facts,
        applicable_rules=applied_rules,
    )

    print()
    print("=" * 100)
    print("GATE RESULT")
    print("=" * 100)

    print(
        "READY:",
        gate_result.ready,
    )

    print()

    if gate_result.missing:

        print(
            "MISSING INFORMATION:"
        )

        print()

        for item in gate_result.missing:

            print(
                f"FIELD: {item.field}"
            )

            print(
                f"QUESTION: {item.question}"
            )

            print(
                f"REASON: {item.reason}"
            )

            print(
                "REQUIRED FOR:",
                ", ".join(
                    item.required_for
                ),
            )

            print()

    else:

        print(
            "NO MANDATORY INFORMATION MISSING."
        )

        print()
        print(
            "BUILDING DESIGN CAN PROCEED."
        )

    print()
    print("=" * 100)

    if gate_result.ready:

        print(
            "PLANNING INPUT GATE: PASSED"
        )

    else:

        print(
            "PLANNING INPUT GATE: USER INPUT REQUIRED"
        )

    print("=" * 100)


if __name__ == "__main__":
    main()