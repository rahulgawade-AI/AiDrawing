from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MandatoryConstraint:
    """
    One mandatory regulatory constraint resolved from an
    authoritative rule.

    The value is NEVER inferred by this class.
    """

    key: str

    value: Any

    unit: str | None

    source_rule_id: str

    regulation_id: str

    rule_name: str

    category: str

    priority: int

    status: str = "verified"

    reason: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(slots=True)
class MandatoryConstraintResult:
    """
    Complete result of mandatory-rule resolution.
    """

    constraints: list[MandatoryConstraint] = field(
        default_factory=list
    )

    applicable_rule_ids: list[str] = field(
        default_factory=list
    )

    unresolved_rule_ids: list[str] = field(
        default_factory=list
    )

    not_applicable_rule_ids: list[str] = field(
        default_factory=list
    )

    invalid_rule_ids: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    @property
    def verified(self) -> bool:
        return bool(self.constraints)

    def by_key(self) -> dict[str, MandatoryConstraint]:
        return {
            constraint.key: constraint
            for constraint in self.constraints
        }
