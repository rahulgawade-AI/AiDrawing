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


TEST_IMAGE = (
    Path(__file__).parent
    / "data"
    / "sample1.png"
)


def main():

    print()
    print("=" * 100)
    print("VISION → PLANNING → DETERMINISTIC RULES")
    print("=" * 100)

    # ==========================================================
    # 1. VISION
    # ==========================================================

    vision = VisionService()

    spatial_context = vision.process(
        TEST_IMAGE
    )

    # ==========================================================
    # 2. USER REQUIREMENTS
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
    # 3. VISION → CANONICAL PLANNING FACTS
    # ==========================================================

    facts = (
        PlanningFacts.from_spatial_context(
            spatial_context,
            user_requirements=user_requirements,
        )
    )

    facts.normalize()

    print()
    print("CANONICAL FACTS")
    print("-" * 100)

    data = facts.to_dict()

    for key, value in data.items():

        print(
            f"{key}: {value}"
        )

    # ==========================================================
    # 4. DETERMINISTIC PLANNING RULES
    # ==========================================================

    print()
    print("RUNNING DETERMINISTIC RULE RESOLVER")
    print("-" * 100)

    planning_service = PlanningService()

    rules = (
        planning_service
        .rule_resolver
        .resolve_building_rules(
            facts
        )
    )

    print(
        "TOTAL RULES:",
        len(rules),
    )

    applicable = []

    unresolved = []

    not_applicable = []

    for rule in rules:

        status = getattr(
            rule,
            "status",
            None,
        )

        rule_id = getattr(
            rule,
            "rule_id",
            None,
        )

        name = getattr(
            rule,
            "name",
            None,
        )

        if status == "applicable":

            applicable.append(
                (
                    rule_id,
                    name,
                )
            )

        elif status == "unresolved":

            unresolved.append(
                (
                    rule_id,
                    name,
                )
            )

        elif status == "not_applicable":

            not_applicable.append(
                (
                    rule_id,
                    name,
                )
            )

    print(
        "APPLICABLE:",
        len(applicable),
    )

    print(
        "UNRESOLVED:",
        len(unresolved),
    )

    print(
        "NOT APPLICABLE:",
        len(not_applicable),
    )

    print()
    print("APPLICABLE RULES")
    print("-" * 100)

    for rule_id, name in applicable:

        print(
            rule_id,
            "|",
            name,
        )

    # ==========================================================
    # 5. VALIDATION
    # ==========================================================

    print()
    print("VALIDATION")
    print("-" * 100)

    assert (
        facts.plot_area == 745.6
    )

    assert (
        facts.plot_number == "78/5"
    )

    assert (
        facts.north_direction == 0.0
    )

    assert (
        facts.requested_units == 6
    )

    assert (
        facts.building_use
        == "residential"
    )

    assert (
        len(rules) > 0
    )

    assert (
        len(applicable) > 0
    )

    print(
        "✓ Vision facts reached PlanningFacts"
    )

    print(
        "✓ User requirements preserved"
    )

    print(
        "✓ Deterministic resolver executed"
    )

    print(
        "✓ Applicable rules found"
    )

    print()
    print("=" * 100)
    print(
        "VISION → PLANNING → RULES PASSED"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()
