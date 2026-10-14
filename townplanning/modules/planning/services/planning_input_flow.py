from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from townplanning.modules.planning.services.planning_input_gate import (
    PlanningInputGate,
    PlanningInputGateResult,
)

from townplanning.modules.planning.services.planning_user_input_resolver import (
    PlanningUserInputResolver,
)

from townplanning.modules.planning.services.planning_requirement_collector import (
    PlanningRequirementCollector,
    PlanningRequirementResult,
)

from townplanning.modules.vision.services.vision_planning_mapper import (
    VisionPlanningMapper,
)


@dataclass(slots=True)
class PlanningInputFlowResult:
    facts: Any
    gate: PlanningInputGateResult

    user_requirements: PlanningRequirementResult | None = None

    vision_mapping: Any | None = None


class PlanningInputFlow:
    """
    Existing planning input flow.

    Coordinates:

        PlanningFacts
            ↓
        Vision evidence
            ↓
        VisionPlanningMapper
            ↓
        PlanningFacts
            ↓
        PlanningInputGate
            ↓
        User requirements
            ↓
        PlanningUserInputResolver
            ↓
        PlanningInputGate

    IMPORTANT:

        Vision does not replace the planning flow.

        Vision only supplies facts/evidence.

        Regulatory derivation remains in the existing
        planning/regulation subsystem.
    """

    def __init__(
        self,
        gate=None,
        resolver=None,
        requirement_collector=None,
        vision_mapper=None,
    ):

        self.gate = (
            gate
            or PlanningInputGate()
        )

        self.resolver = (
            resolver
            or PlanningUserInputResolver()
        )

        self.requirement_collector = (
            requirement_collector
            or PlanningRequirementCollector()
        )

        self.vision_mapper = (
            vision_mapper
            or VisionPlanningMapper()
        )

    def evaluate(
        self,
        facts,
        applicable_rules=None,
    ) -> PlanningInputFlowResult:

        gate_result = self.gate.evaluate(
            facts,
            applicable_rules=applicable_rules,
        )

        user_requirements = (
            self.requirement_collector.evaluate(
                facts
            )
        )

        return PlanningInputFlowResult(
            facts=facts,
            gate=gate_result,
            user_requirements=user_requirements,
        )

    def evaluate_input(
        self,
        facts,
        user_input=None,
        images=None,
        applicable_rules=None,
        vision_evidence=None,
    ):

        # ---------------------------------------------------------
        # 1. Vision evidence -> PlanningFacts
        # ---------------------------------------------------------

        vision_mapping = None

        if vision_evidence is not None:

            vision_mapping = (
                self.vision_mapper.map(
                    facts=facts,
                    evidence=vision_evidence,
                )
            )

        # ---------------------------------------------------------
        # 2. Existing gate
        # ---------------------------------------------------------

        result = self.evaluate(
            facts,
            applicable_rules=applicable_rules,
        )

        # ---------------------------------------------------------
        # 3. User input
        # ---------------------------------------------------------

        if user_input:

            facts = self.resolver.apply(
                facts,
                result.gate.missing,
                user_input,
            )

            result = self.evaluate(
                facts,
                applicable_rules=applicable_rules,
            )

        result.vision_mapping = (
            vision_mapping
        )

        return result

    def apply_user_input(
        self,
        facts,
        gate_result,
        user_input,
        applicable_rules=None,
    ):

        facts = self.resolver.apply(
            facts,
            gate_result.missing,
            user_input,
        )

        return self.evaluate(
            facts,
            applicable_rules=applicable_rules,
        )
