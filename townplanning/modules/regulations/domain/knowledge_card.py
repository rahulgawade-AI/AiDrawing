"""
Structured engineering knowledge extracted from a regulation.

This object becomes the primary knowledge source for:

- Question Answering
- Compliance Checking
- FSI Calculator
- Layout Generator
- Drawing Generator
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class KnowledgeCard:

    # --------------------------------------------------
    # Identity
    # --------------------------------------------------

    id: str

    regulation_id: str

    title: str

    # --------------------------------------------------
    # High-level understanding
    # --------------------------------------------------

    summary: str

    purpose: str

    scope: str = ""

    # --------------------------------------------------
    # Engineering knowledge
    # --------------------------------------------------

    definitions: list[str] = field(default_factory=list)

    permissions: list[str] = field(default_factory=list)

    conditions: list[str] = field(default_factory=list)

    prohibitions: list[str] = field(default_factory=list)

    measurements: list[str] = field(default_factory=list)

    exceptions: list[str] = field(default_factory=list)

    # --------------------------------------------------
    # Applicability
    # --------------------------------------------------

    applicability: list[str] = field(default_factory=list)

    authority: str = ""

    inputs: list[str] = field(default_factory=list)

    outputs: list[str] = field(default_factory=list)

    # --------------------------------------------------
    # References
    # --------------------------------------------------

    references: list[str] = field(default_factory=list)

    related_regulations: list[str] = field(default_factory=list)

    # --------------------------------------------------
    # AI
    # --------------------------------------------------

    keywords: list[str] = field(default_factory=list)

    examples: list[str] = field(default_factory=list)

    notes: list[str] = field(default_factory=list)

    # --------------------------------------------------

    metadata: dict = field(default_factory=dict)