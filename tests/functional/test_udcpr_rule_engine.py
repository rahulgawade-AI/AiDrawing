from townplanning.infrastructure.database.models.rule_model import RuleModel
from townplanning.infrastructure.database.session import SessionLocal

from townplanning.modules.planning.rules.rule_engine import (
    UDCPRRuleEngine,
)


def main():

    session = SessionLocal()

    try:

        models = (
            session.query(RuleModel)
            .filter(
                RuleModel.enabled.is_(True)
            )
            .all()
        )

        # Convert DB models to domain Rules using
        # the existing mapper already used by the
        # RuleRepository.
        from townplanning.infrastructure.database.mappers import (
            RuleMapper,
        )

        rules = [
            RuleMapper.to_domain(model)
            for model in models
        ]

        facts = {
    "plot_area": 745.6,
    "plot_area_sqm": 745.6,

    "road_width": 18.0,
    "road_width_m": 18.0,
    "road_width_meters": 18.0,

    "building_type": "Residential",
    "building_use": "residential",

    "development_type": "green-field development",
    "project_type": "green-field development",

    "maximize_fsi": True,

    # These are intentionally unknown until
    # site/zoning information is available.
    "zone_type": None,
    "land_use_zone": None,
    "municipality": None,
    "location": None,

    "building_height": None,
    "building_height_meters": None,
    "number_of_floors": None,

    "tod": None,
}

        engine = UDCPRRuleEngine()

        results = engine.evaluate(
            rules,
            facts,
        )

        applicable = [
            r
            for r in results
            if r.status == "applicable"
        ]

        unresolved = [
            r
            for r in results
            if r.status == "unresolved"
        ]

        rejected = [
            r
            for r in results
            if r.status == "not_applicable"
        ]

        print()
        print("=" * 100)
        print("UDCPR RULE ENGINE")
        print("=" * 100)

        print(
            "TOTAL RULES       :",
            len(results),
        )

        print(
            "APPLICABLE        :",
            len(applicable),
        )

        print(
            "NOT APPLICABLE    :",
            len(rejected),
        )

        print(
            "UNRESOLVED        :",
            len(unresolved),
        )

        print()
        print("=" * 100)
        print("APPLICABLE RULES")
        print("=" * 100)

        for rule in applicable:

            print(
                f"[{rule.category}] "
                f"{rule.name}"
            )

        print()
        print("=" * 100)
        print("UNRESOLVED RULES")
        print("=" * 100)

        for rule in unresolved:

            print(
                f"[{rule.category}] "
                f"{rule.name}"
                f" -> {rule.reason}"
            )

    finally:

        session.close()


if __name__ == "__main__":
    main()
