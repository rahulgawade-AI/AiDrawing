from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ApplicableRule:
    """
    Result of evaluating one UDCPR rule against
    the current planning facts.
    """

    rule_id: str
    regulation_id: str

    category: str
    name: str
    description: str

    priority: int

    status: str
    """
    One of:

        applicable
        not_applicable
        unresolved
        invalid
    """

    condition: dict[str, Any] = field(
        default_factory=dict
    )

    result: dict[str, Any] = field(
        default_factory=dict
    )

    reason: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def is_applicable(self) -> bool:
        return self.status == "applicable"

    @property
    def is_unresolved(self) -> bool:
        return self.status == "unresolved"
