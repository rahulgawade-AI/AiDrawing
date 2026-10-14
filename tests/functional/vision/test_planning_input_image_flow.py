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


class FakeVisionOllama:
    """
    Deterministic vision-model test double.

    No real Ollama request is made.
    The response simulates facts that a vision + text
    extraction model could return from the supplied
    site image and user description.
    """

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        images=None,
    ) -> str:

        assert temperature == 0.0

        self.calls.append(
            {
                "prompt": prompt,
                "images": images or [],
            }
        )

        return json.dumps(
            {
                "facts": {
                    # Site / plot facts
                    "plot_area": 2000,
                    "plot_width": 40,
                    "plot_depth": 50,

                    # Road/access
                    "road_width": 12,

                    # Building/program inputs
                    "building_use": "residential",
                    "number_of_floors": 12,
                    "requested_height": 36,

                    # Residential requirement
                    "requested_2bhk_units": 12,
                    "requested_3bhk_units": 8,

                    # Existing condition
                    "existing_building": False,
                    "redevelopment": False,
                },

                "conflicts": [],

                "unreadable_or_uncertain": [],
            }
        )


def main() -> None:

    print("=" * 70)
    print("PLANNING INPUT IMAGE + USER TEXT INTEGRATION TEST")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. Locate test image
    # ---------------------------------------------------------

    image_candidates = [
        Path("tests/fixtures/site.png"),
        Path("tests/fixtures/site.jpg"),
        Path("tests/fixtures/plot.png"),
        Path("tests/fixtures/plot.jpg"),
        Path("data/test/site.png"),
        Path("data/test/site.jpg"),
    ]

    image_path = next(
        (p for p in image_candidates if p.exists()),
        None,
    )

    if image_path is None:
        print()
        print("WARNING: No test image found.")
        print()
        print("Create one of:")
        for path in image_candidates:
            print(f"  {path}")
        print()
        print(
            "The test will continue with a simulated image path "
            "so the resolver/image plumbing can still be verified."
        )

        image_path = Path("tests/fixtures/site.png")

    print()
    print("Image:")
    print(f"  {image_path}")

    # ---------------------------------------------------------
    # 2. Create PlanningFacts
    # ---------------------------------------------------------

    facts = PlanningFacts()

    print()
    print("Initial PlanningFacts:")
    print(f"  plot_area      = {facts.plot_area}")
    print(f"  plot_width     = {facts.plot_width}")
    print(f"  plot_depth     = {facts.plot_depth}")
    print(f"  road_width     = {facts.road_width}")
    print(f"  building_use   = {facts.building_use}")

    # ---------------------------------------------------------
    # 3. Inject deterministic vision/Ollama client
    # ---------------------------------------------------------

    ollama = FakeVisionOllama()

    resolver = PlanningUserInputResolver(
        ollama_client=ollama,
    )

    # ---------------------------------------------------------
    # 4. Use EXISTING PlanningInputFlow
    # ---------------------------------------------------------

    flow = PlanningInputFlow(
        resolver=resolver,
    )

    user_input = (
        "Design a residential apartment building on this plot. "
        "The plot is approximately 2000 square metres, "
        "40 metres wide and 50 metres deep, with a 12 metre road. "
        "I want 12 floors and approximately 36 metres height. "
        "Provide 12 two-BHK units and 8 three-BHK units. "
        "There is no existing building. "
        "Maximize usable area and parking."
    )

    print()
    print("User input:")
    print(f"  {user_input}")

    # ---------------------------------------------------------
    # 5. Run actual existing flow
    # ---------------------------------------------------------

    result = flow.evaluate_input(
        facts=facts,
        user_input=user_input,
        images=[str(image_path)],
    )

    # ---------------------------------------------------------
    # 6. Display extracted facts
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("EXTRACTED PLANNING FACTS")
    print("=" * 70)

    expected = {
        "plot_area": 2000,
        "plot_width": 40,
        "plot_depth": 50,
        "road_width": 12,
        "building_use": "residential",
        "number_of_floors": 12,
        "requested_height": 36,
        "requested_2bhk_units": 12,
        "requested_3bhk_units": 8,
        "existing_building": False,
        "redevelopment": False,
    }

    failures: list[str] = []

    for field_name, expected_value in expected.items():

        actual_value = getattr(
            facts,
            field_name,
            None,
        )

        print(
            f"{field_name:25s}: "
            f"{actual_value!r}"
        )

        if actual_value != expected_value:
            failures.append(
                f"{field_name}: "
                f"expected={expected_value!r}, "
                f"actual={actual_value!r}"
            )

    # ---------------------------------------------------------
    # 7. Regulatory safety check
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("REGULATORY OUTPUT CHECK")
    print("=" * 70)

    print(
        "basic_fsi   :",
        facts.basic_fsi,
    )

    print(
        "maximum_fsi :",
        facts.maximum_fsi,
    )

    if facts.basic_fsi is not None:
        failures.append(
            f"basic_fsi must remain None; "
            f"got {facts.basic_fsi!r}"
        )

    if facts.maximum_fsi is not None:
        failures.append(
            f"maximum_fsi must remain None; "
            f"got {facts.maximum_fsi!r}"
        )

    # ---------------------------------------------------------
    # 8. Verify image reached resolver
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("IMAGE PIPELINE CHECK")
    print("=" * 70)

    if not ollama.calls:
        failures.append(
            "Ollama client was never called."
        )
    else:
        received_images = ollama.calls[0]["images"]

        print(
            "Images passed to resolver:",
            received_images,
        )

        if str(image_path) not in received_images:
            failures.append(
                "Expected image path was not passed "
                "to the Ollama client."
            )

    # ---------------------------------------------------------
    # 9. Gate result
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("PLANNING INPUT GATE")
    print("=" * 70)

    print(
        "Missing facts:",
        len(result.gate.missing),
    )

    for missing in result.gate.missing:
        print(
            " -",
            missing,
        )

    # ---------------------------------------------------------
    # 10. Final result
    # ---------------------------------------------------------

    print()
    print("=" * 70)

    if failures:
        print("TEST FAILED")
        print("=" * 70)

        for failure in failures:
            print(" -", failure)

        raise SystemExit(1)

    print("TEST PASSED")
    print("=" * 70)

    print()
    print(
        "Existing PlanningInputFlow successfully connected:"
    )
    print(
        "  user text + image"
    )
    print(
        "        -> PlanningUserInputResolver"
    )
    print(
        "        -> Ollama vision/text extraction"
    )
    print(
        "        -> PlanningFacts"
    )
    print(
        "        -> PlanningInputGate"
    )


if __name__ == "__main__":
    main()
