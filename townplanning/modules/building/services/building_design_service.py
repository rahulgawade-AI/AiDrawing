from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from townplanning.modules.building.domain.building_design_plan import (
    BuildingDesignPlan,
)
from townplanning.modules.building.services.building_design_generator import (
    BuildingDesignGenerator,
)
from townplanning.modules.planning.domain.planning_constraints import (
    PlanningConstraints,
)
from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)
from townplanning.modules.planning.services.planning_service import (
    PlanningService,
)


@dataclass(slots=True)
class BuildingDesignResult:
    """
    Result of:

        PlanningFacts
            ->
        PlanningService
            ->
        PlanningConstraints
            ->
        BuildingDesignPlan
    """

    facts: PlanningFacts

    constraints: PlanningConstraints

    design_plan: BuildingDesignPlan

    def to_dict(self) -> dict[str, Any]:

        return {
            "facts": self.facts.to_dict(),

            "constraints": {
                key: value
                for key, value in self._constraints_to_dict().items()
                if key not in {
                    "applied_rules",
                    "unresolved_rules",
                    "rejected_rules",
                }
            },

            "design_plan": self.design_plan.to_dict(),
        }

    def _constraints_to_dict(
        self,
    ) -> dict[str, Any]:

        result: dict[str, Any] = {}

        fields = getattr(
            self.constraints,
            "__dataclass_fields__",
            {},
        )

        for name in fields:

            try:

                result[name] = getattr(
                    self.constraints,
                    name,
                )

            except Exception:

                continue

        return result


class BuildingDesignService:
    """
    Orchestrates deterministic planning followed by the
    building-design planning stage.

    No regulatory values are calculated here.

    PlanningService is authoritative for deterministic
    planning rules.
    """

    def __init__(
        self,
        planning_service: PlanningService | None = None,
        generator: BuildingDesignGenerator | None = None,
    ):

        self.planning_service = (
            planning_service
            if planning_service is not None
            else PlanningService()
        )

        self.generator = (
            generator
            if generator is not None
            else BuildingDesignGenerator()
        )

    def generate(
        self,
        facts: PlanningFacts,
    ) -> BuildingDesignResult:

        if facts is None:

            raise ValueError(
                "PlanningFacts are required."
            )

        constraints = (
            self.planning_service.evaluate(
                facts
            )
        )

        design_plan = (
            self.generator.generate(
                facts,
                constraints,
            )
        )

        return BuildingDesignResult(
            facts=facts,
            constraints=constraints,
            design_plan=design_plan,
        )

    def close(self) -> None:

        close = getattr(
            self.planning_service,
            "close",
            None,
        )

        if callable(close):

            close()
