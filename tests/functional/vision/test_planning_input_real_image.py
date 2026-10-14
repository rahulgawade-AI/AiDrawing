from __future__ import annotations

import json
from pathlib import Path

from townplanning.modules.planning.domain.planning_facts import PlanningFacts
from townplanning.modules.planning.services.planning_input_flow import (
    PlanningInputFlow,
)
from townplanning.modules.planning.services.planning_user_input_resolver import (
    PlanningUserInputResolver,
)
from townplanning.modules.planning.llm.ollama_client import OllamaClient


IMAGE = Path(
    "tests/functional/vision/data/sample1.png"
)


USER_INPUT = """
I want to develop this plot as a residential apartment building.

Use the uploaded site/plot image to identify whatever site
information can be reliably determined from the image.

Do not assume measurements that cannot be read reliably.

My requirements are:

- Residential apartment building
- New construction
- Maximize usable residential area
- Maximize parking
- Optimize daylight and ventilation

If information cannot be reliably determined from the image
or this description, leave it unknown.

Do not calculate FSI, setbacks, margins, parking requirements,
fire requirements, permissible height, or any other regulatory
requirement. Those will be determined later by the deterministic
UDCPR rule engine.
"""


def main() -> None:

    if not IMAGE.exists():
        raise SystemExit(
            f"Image does not exist: {IMAGE}"
        )

    print("=" * 80)
    print("REAL IMAGE -> OLLAMA VISION -> PLANNING FACTS")
    print("=" * 80)

    print()
    print("Image:")
    print(" ", IMAGE.resolve())

    facts = PlanningFacts()

    client = OllamaClient()

    resolver = PlanningUserInputResolver(
        ollama_client=client,
    )

    flow = PlanningInputFlow(
        resolver=resolver,
    )

    print()
    print("User input:")
    print(USER_INPUT.strip())

    print()
    print("=" * 80)
    print("RUNNING REAL OLLAMA VISION EXTRACTION")
    print("=" * 80)

    result = flow.evaluate_input(
        facts=facts,
        user_input=USER_INPUT,
        images=[str(IMAGE.resolve())],
    )

    print()
    print("=" * 80)
    print("EXTRACTED PLANNING FACTS")
    print("=" * 80)

    data = facts.to_dict()

    print(
        json.dumps(
            data,
            indent=2,
            default=str,
            ensure_ascii=False,
        )
    )

    print()
    print("=" * 80)
    print("GATE / MISSING INFORMATION")
    print("=" * 80)

    print(
        "Missing facts:",
        len(result.gate.missing),
    )

    for item in result.gate.missing:
        print()
        print("FIELD       :", item.field)
        print("QUESTION    :", item.question)
        print("REASON      :", item.reason)
        print(
            "REQUIRED FOR:",
            ", ".join(item.required_for),
        )

    print()
    print("=" * 80)
    print("REGULATORY SAFETY CHECK")
    print("=" * 80)

    print("basic_fsi   :", facts.basic_fsi)
    print("maximum_fsi :", facts.maximum_fsi)

    print()
    print("=" * 80)
    print("RESULT")
    print("=" * 80)

    print(
        "Real image was supplied to the existing "
        "PlanningInputFlow."
    )

    print(
        "Facts that can be reliably extracted are "
        "stored in PlanningFacts."
    )

    print(
        "Unknown information remains missing and is "
        "reported by PlanningInputGate."
    )


if __name__ == "__main__":
    main()
