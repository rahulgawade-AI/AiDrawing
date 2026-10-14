from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.planning.mandatory.mandatory_rule_engine import (
    MandatoryRuleEngine,
)


def main():

    print()
    print("=" * 100)
    print("MANDATORY RULE ENGINE")
    print("=" * 100)

    facts = PlanningFacts(
        plot_area=745.6,
        road_width=12.0,

        city="Pune",
        district="Pune",
        state="Maharashtra",

        building_type="Residential building",
        building_use="residential",

        congested_area=False,

        tod_zone=False,
        heritage_zone=False,
        crz_zone=False,
        eco_sensitive_zone=False,
        airport_restriction=False,

        redevelopment=False,
    )

    print()
    print("PLANNING FACTS")
    print("-" * 100)

    print("plot_area       :", facts.plot_area)
    print("road_width      :", facts.road_width)
    print("city            :", facts.city)
    print("district        :", facts.district)
    print("building_type   :", facts.building_type)
    print("building_use    :", facts.building_use)
    print("congested_area  :", facts.congested_area)

    engine = MandatoryRuleEngine()

    result = engine.resolve(
        facts
    )

    print()
    print("=" * 100)
    print("MANDATORY CONSTRAINTS")
    print("=" * 100)

    if not result.constraints:
        print("NO VERIFIED MANDATORY CONSTRAINTS")

    for constraint in result.constraints:

        print()
        print(
            f"{constraint.key}: "
            f"{constraint.value} "
            f"{constraint.unit or ''}"
        )

        print(
            "  status       :",
            constraint.status,
        )

        print(
            "  rule_id      :",
            constraint.source_rule_id,
        )

        print(
            "  regulation_id:",
            constraint.regulation_id,
        )

        print(
            "  rule         :",
            constraint.rule_name,
        )

    print()
    print("=" * 100)
    print("RULE STATISTICS")
    print("=" * 100)

    print(
        "APPLICABLE     :",
        len(result.applicable_rule_ids),
    )

    print(
        "UNRESOLVED     :",
        len(result.unresolved_rule_ids),
    )

    print(
        "NOT APPLICABLE :",
        len(result.not_applicable_rule_ids),
    )

    print(
        "INVALID        :",
        len(result.invalid_rule_ids),
    )

    if result.warnings:

        print()
        print("WARNINGS")
        print("-" * 100)

        for warning in result.warnings:
            print("-", warning)

    print()
    print("=" * 100)
    print("MANDATORY RULE ENGINE TEST COMPLETED")
    print("=" * 100)


if __name__ == "__main__":
    main()
