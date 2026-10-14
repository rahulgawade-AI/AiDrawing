from __future__ import annotations

import json
from pathlib import Path

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.vision.ai.vision_analyzer import (
    VisionAnalyzer,
)

from townplanning.modules.vision.services.vision_planning_mapper import (
    VisionPlanningMapper,
)

from townplanning.modules.planning.services.planning_requirement_collector import (
    PlanningRequirementCollector,
)


BASE = Path(
    "tests/functional/vision/data"
)

IMAGES = [
    BASE / "sample1.png",
    BASE / "sample2.png",
    BASE / "sample3.png",
    BASE / "sample4.png",
]


def value(facts, name):
    try:
        value = getattr(
            facts,
            name,
            None,
        )

        if value is not None:
            return value

        values = getattr(
            facts,
            "values",
            None,
        )

        if isinstance(values, dict):
            return values.get(name)

    except Exception:
        pass

    return None


analyzer = VisionAnalyzer()
mapper = VisionPlanningMapper()
requirements = PlanningRequirementCollector()


for image in IMAGES:

    print()
    print("=" * 100)
    print("IMAGE:", image.name)
    print("=" * 100)

    if not image.exists():
        print("NOT FOUND:", image)
        continue

    facts = PlanningFacts()

    evidence = analyzer.analyze(
        image
    )

    mapping = mapper.map(
        facts=facts,
        evidence=evidence,
    )

    requirement_result = requirements.evaluate(
        facts
    )

    print()
    print("IMAGE TYPE:")
    print(
        evidence.image_type,
        evidence.image_type_confidence,
    )

    print()
    print("MAPPED FACTS:")

    for field_name in mapping.mapped_fields:

        print(
            f"  {field_name}:",
            value(
                facts,
                field_name,
            ),
        )

    print()
    print("IMAGE REGULATORY FACTS:")

    if mapping.image_regulatory_fields:

        for field_name in (
            mapping.image_regulatory_fields
        ):

            print(
                f"  {field_name}:",
                value(
                    facts,
                    field_name,
                ),
            )

            print(
                "    SOURCE:",
                getattr(
                    facts,
                    "fact_sources",
                    {},
                ).get(field_name),
            )

    else:

        print("  NONE")

    print()
    print("MISSING USER REQUIREMENTS:")

    if requirement_result.missing:

        for question in (
            requirement_result.missing
        ):

            prefix = (
                "REQUIRED"
                if question.required
                else "OPTIONAL"
            )

            print(
                f"  [{prefix}] "
                f"{question.field}: "
                f"{question.question}"
            )

            if question.options:

                print(
                    "       OPTIONS:",
                    ", ".join(
                        question.options
                    ),
                )

    else:

        print("  NONE")

    print()
    print("SUMMARY:")

    print(
        json.dumps(
            {
                "image": image.name,
                "image_type": evidence.image_type,
                "mapped_fields": (
                    mapping.mapped_fields
                ),
                "image_regulatory_fields": (
                    mapping.image_regulatory_fields
                ),
                "missing_user_fields": [
                    question.field
                    for question
                    in requirement_result.missing
                ],
            },
            indent=2,
        )
    )
