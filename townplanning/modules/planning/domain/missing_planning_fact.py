from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MissingPlanningFact:
    """
    A planning fact required before building design
    can proceed.

    The value must be supplied by the user or obtained
    from another authoritative source.

    The system must never invent the value.
    """

    field: str

    question: str

    reason: str = ""

    required_for: list[str] = field(
        default_factory=list
    )

    @property
    def key(self) -> str:
        return self.field
