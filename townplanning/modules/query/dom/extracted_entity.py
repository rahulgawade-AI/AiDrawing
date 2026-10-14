from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExtractedEntity:
    """
    Represents an entity extracted from a user query.
    """

    entity_type: str

    value: str

    confidence: float = 1.0