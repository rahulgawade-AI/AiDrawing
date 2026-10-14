from __future__ import annotations

import json

from townplanning.modules.planning.domain.planning_facts import PlanningFacts
from townplanning.modules.planning.services.planning_input_flow import PlanningInputFlow


class FakeOllama:
    """Deterministic test double; no Ollama request is made."""

    def generate(self, prompt: str, *, temperature: float = 0.0, images=None) -> str:
        assert temperature == 0.0
        return json.dumps({
            "facts": {
                "plot_area": 2000,
                "plot_width": 40,
                "plot_depth": 50,
                "road_width": 12,
                "building_use": "residential",
                "requested_2bhk_units": 12,
                "requested_3bhk_units": 8,
            },
            "conflicts": [],
            "unreadable_or_uncertain": [],
        })


class TestResolver:
    def __init__(self):
        from townplanning.modules.planning.services.planning_user_input_resolver import (
            PlanningUserInputResolver,
        )
        self.resolver = PlanningUserInputResolver()


def main() -> None:
    facts = PlanningFacts()
    resolver = TestResolver().resolver

    resolver.extract_and_apply(
        facts,
        user_input="Residential building on a 2000 sq.m plot, 12 m road. Need 12 2BHK and 8 3BHK.",
        client=FakeOllama(),
    )

    assert facts.plot_area == 2000
    assert facts.road_width == 12
    assert facts.building_use == "residential"
    assert facts.requested_2bhk_units == 12
    assert facts.requested_3bhk_units == 8

    # Regulatory values must not be accepted from Ollama.
    assert facts.basic_fsi is None
    assert facts.maximum_fsi is None

    result = PlanningInputFlow(
        resolver=resolver,
    ).evaluate(facts)

    print("Planning input Ollama integration test: PASS")
    print("Extracted facts:")
    print(json.dumps(facts.to_dict(), indent=2, default=str))
    print("Missing facts:", len(result.gate.missing))


if __name__ == "__main__":
    main()
