from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from townplanning.modules.regulations.domain.rule import Rule

from townplanning.modules.planning.domain.applicable_rule import (
    ApplicableRule,
)

from .rule_condition_engine import (
    RuleConditionEngine,
)


class UDCPRRuleEngine:
    """
    Central deterministic UDCPR applicability engine.

    This engine does NOT calculate the final building design.

    Its job is to answer:

        Which rules apply?

    and preserve:

        Which rules do not apply?
        Which rules cannot yet be evaluated?
        Why?
    """

    def __init__(
        self,
        condition_engine: RuleConditionEngine | None = None,
    ):

        self.conditions = (
            condition_engine
            or RuleConditionEngine()
        )

    # ---------------------------------------------------------

    def evaluate(
        self,
        rules: Iterable[Rule],
        facts: dict[str, Any],
    ) -> list[ApplicableRule]:

        results: list[ApplicableRule] = []

        for rule in rules:

            if not rule.enabled:

                results.append(
                    self._result(
                        rule,
                        status="not_applicable",
                        reason="Rule is disabled.",
                    )
                )

                continue

            evaluation = (
                self.conditions.evaluate(
                    rule.condition,
                    facts,
                )
            )

            results.append(
                self._result(
                    rule,
                    status=evaluation.status,
                    reason=evaluation.reason,
                )
            )

        return sorted(
            results,
            key=lambda item: (
                item.priority,
                item.category,
                item.name,
            ),
        )

    # ---------------------------------------------------------

    def applicable(
        self,
        rules: Iterable[Rule],
        facts: dict[str, Any],
    ) -> list[ApplicableRule]:

        return [
            result
            for result in self.evaluate(
                rules,
                facts,
            )
            if result.is_applicable
        ]

    # ---------------------------------------------------------

    def unresolved(
        self,
        rules: Iterable[Rule],
        facts: dict[str, Any],
    ) -> list[ApplicableRule]:

        return [
            result
            for result in self.evaluate(
                rules,
                facts,
            )
            if result.is_unresolved
        ]

    # ---------------------------------------------------------

    def by_category(
        self,
        rules: Iterable[Rule],
        facts: dict[str, Any],
    ) -> dict[str, list[ApplicableRule]]:

        grouped: dict[
            str,
            list[ApplicableRule],
        ] = defaultdict(list)

        for result in self.applicable(
            rules,
            facts,
        ):

            grouped[
                result.category
            ].append(
                result
            )

        return dict(grouped)

    # ---------------------------------------------------------

    @staticmethod
    def _result(
        rule: Rule,
        status: str,
        reason: str,
    ) -> ApplicableRule:

        return ApplicableRule(

            rule_id=rule.id,

            regulation_id=rule.regulation_id,

            category=rule.category,

            name=rule.name,

            description=rule.description,

            priority=rule.priority,

            status=status,

            condition=dict(
                rule.condition or {}
            ),

            result=dict(
                rule.result or {}
            ),

            reason=reason,

            metadata=dict(
                rule.metadata or {}
            ),
        )
