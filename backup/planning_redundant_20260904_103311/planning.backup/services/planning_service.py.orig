from __future__ import annotations

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.planning.domain.planning_constraints import (
    PlanningConstraints,
)

from townplanning.modules.planning.regulations.udcpr_rule_resolver import (
    UDCPRRuleResolver,
)

from townplanning.modules.planning.regulations.constraint_calculator import (
    ConstraintCalculator,
)


class PlanningService:
    """
    Main entry point for the deterministic UDCPR
    planning engine.

    Pipeline:

        Site Facts
            ↓
        Rule Resolver
            ↓
        Applicable UDCPR Rules
            ↓
        Constraint Calculator
            ↓
        Planning Constraints
    """

    def __init__(self):

        self.rule_resolver = (
            UDCPRRuleResolver()
        )

        self.constraint_calculator = (
            ConstraintCalculator()
        )

    def evaluate(
        self,
        facts: PlanningFacts,
    ) -> PlanningConstraints:

        rules = (
            self.rule_resolver
            .resolve_building_rules(
                facts
            )
        )

        constraints = (
            self.constraint_calculator.calculate(
                facts,
                rules,
            )
        )

        return constraints