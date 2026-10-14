from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiscoveredConstraint:
    """
    A regulatory constraint discovered from the UDCPR
    knowledge available to the planning system.

    This is deliberately dynamic. New constraint types do not
    require changes to PlanningConstraints.
    """

    constraint_id: str
    name: str

    category: str

    value: Any = None
    unit: str | None = None

    operator: str | None = None

    status: str = "unresolved"

    applicability: str | None = None

    source_rule_ids: list[str] = field(default_factory=list)

    source_tables: list[str] = field(default_factory=list)

    source_pages: list[int] = field(default_factory=list)

    rationale: str | None = None

    dependencies: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstraintDiscoveryResult:
    """
    Result returned by the Ollama constraint discovery layer.
    """

    status: str

    constraints: list[DiscoveredConstraint] = field(
        default_factory=list
    )

    unresolved: list[dict[str, Any]] = field(
        default_factory=list
    )

    source_context: dict[str, Any] = field(
        default_factory=dict
    )

    model: str | None = None

    raw_response: str | None = None