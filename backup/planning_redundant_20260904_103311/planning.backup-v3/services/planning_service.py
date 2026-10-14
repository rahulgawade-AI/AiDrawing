from __future__ import annotations

from typing import Any

from townplanning.modules.planning.domain.planning_facts import PlanningFacts
from townplanning.modules.planning.domain.planning_constraints import PlanningConstraints
from townplanning.modules.planning.regulations.udcpr_rule_resolver import UDCPRRuleResolver
from townplanning.modules.planning.regulations.constraint_calculator import ConstraintCalculator


class PlanningService:
    """Main deterministic entry point for the UDCPR planning engine.

    The service deliberately separates:

    * raw/canonical planning facts; and
    * derived regulatory facts produced by deterministic calculation.

    This is important because UDCPR rules can depend on values calculated
    by earlier rules (for example ``calculated_fsi`` versus a Table 6-G
    building potential).  Raw PlanningFacts are never mutated to satisfy
    such rules.
    """

    def __init__(self):
        self.rule_resolver = UDCPRRuleResolver()
        self.constraint_calculator = ConstraintCalculator()

    @staticmethod
    def _derived_facts(
        facts: PlanningFacts,
        constraints: PlanningConstraints,
    ) -> dict[str, Any]:
        """Build deterministic facts needed by dependent UDCPR rules.

        ``calculated_fsi`` here intentionally means the FSI already
        established before a premium/additional-FSI permission is granted.
        Premium FSI is therefore not circularly used to prove its own
        eligibility.
        """
        base_components = [
            constraints.basic_fsi,
            constraints.tdr_fsi,
            constraints.incentive_fsi,
        ]
        calculated_fsi = sum(
            value for value in base_components if value is not None
        )

        derived: dict[str, Any] = {
            "basic_fsi": constraints.basic_fsi,
            "calculated_fsi": calculated_fsi,
            "maximum_fsi": constraints.maximum_fsi,
            "maximum_building_potential_table_6g": constraints.maximum_fsi,
        }

        if facts.plot_area is not None:
            derived["plot_area_for_fsi"] = facts.plot_area

        # A proposed/requested height or a requested floor count is a valid
        # derived input for threshold rules (fire lift, refuge area, road
        # width checks, etc.).  It is deliberately NOT treated as a maximum
        # permissible height.
        proposed_height = facts.building_height
        if proposed_height is None:
            proposed_height = facts.requested_height
        if proposed_height is None and facts.requested_floors is not None and facts.floor_height is not None:
            proposed_height = facts.requested_floors * facts.floor_height
        if proposed_height is not None:
            derived["building_height"] = proposed_height
            derived["proposed_building_height"] = proposed_height

        if facts.requested_floors is not None:
            derived["number_of_floors"] = facts.requested_floors

        # Remove unknown/None derived values so a missing value remains
        # genuinely unresolved in the condition engine.
        return {key: value for key, value in derived.items() if value is not None}

    @staticmethod
    def _merge_rules(
        first: list,
        second: list,
    ) -> list:
        """Prefer the latest evaluation for each database rule."""
        merged = {str(rule.rule_id): rule for rule in first}
        for rule in second:
            merged[str(rule.rule_id)] = rule
        return list(merged.values())

    def evaluate(self, facts: PlanningFacts) -> PlanningConstraints:
        # Pass 1: evaluate directly against authoritative raw facts.
        first_rules = self.rule_resolver.resolve_building_rules(facts)
        first_constraints = self.constraint_calculator.calculate(
            facts,
            first_rules,
        )

        # Pass 2: expose only deterministic values already calculated by
        # Pass 1.  This resolves dependent rules without modifying facts.
        derived = self._derived_facts(facts, first_constraints)
        second_rules = self.rule_resolver.resolve_building_rules(
            facts,
            extra_facts=derived,
        )

        rules = self._merge_rules(first_rules, second_rules)
        constraints = self.constraint_calculator.calculate(facts, rules)

        constraints.metadata.update({
            "derived_regulatory_facts": derived,
            "evaluation_passes": 2,
        })

        return constraints
