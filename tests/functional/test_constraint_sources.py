from __future__ import annotations

import json

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.infrastructure.database.models.rule_model import RuleModel


TARGETS = {
    "tdr_fsi": [
        "tdr",
        "transferable",
        "development rights",
    ],
    "incentive_fsi": [
        "incentive",
        "additional fsi",
    ],
    "maximum_ground_coverage": [
        "ground coverage",
        "coverage",
    ],
    "setbacks": [
        "setback",
        "margin",
        "marginal open space",
    ],
    "height": [
        "height",
        "storey",
        "storeys",
        "floor",
    ],
    "parking_area": [
        "parking area",
        "parking space",
    ],
}


def main():
    session = SessionLocal()

    try:
        rules = (
            session.query(RuleModel)
            .filter(RuleModel.enabled.is_(True))
            .order_by(RuleModel.priority.asc())
            .all()
        )

        print("=" * 110)
        print("UDCPR RULE SOURCE DIAGNOSTIC")
        print("=" * 110)

        for rule in rules:

            category = str(
                getattr(rule, "category", "") or ""
            )

            name = str(
                getattr(rule, "name", "") or ""
            )

            searchable = (
                f"{category} {name}"
            ).lower()

            matched = []

            for target, keywords in TARGETS.items():
                if any(
                    keyword in searchable
                    for keyword in keywords
                ):
                    matched.append(target)

            if not matched:
                continue

            print()
            print("-" * 110)
            print("RULE ID :", rule.id)
            print("CATEGORY:", category)
            print("NAME    :", name)
            print("TARGETS :", ", ".join(matched))
            print("STATUS  : enabled")

            print("CONDITION:")
            print(
                json.dumps(
                    rule.condition_json or {},
                    indent=2,
                    ensure_ascii=False,
                )
            )

            print("RESULT:")
            print(
                json.dumps(
                    rule.result_json or {},
                    indent=2,
                    ensure_ascii=False,
                )
            )

        print()
        print("=" * 110)
        print("END")
        print("=" * 110)

    finally:
        session.close()


if __name__ == "__main__":
    main()
