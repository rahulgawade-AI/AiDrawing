from __future__ import annotations

from dataclasses import dataclass, field

from townplanning.modules.query.dom.extracted_entity import (
    ExtractedEntity,
)
from townplanning.modules.query.dom.query_intent import (
    QueryIntent,
)


@dataclass(slots=True)
class Query:
    """
    Normalized query produced by the query processor.
    """

    original: str

    normalized: str

    expanded: str

    intent: QueryIntent = QueryIntent.UNKNOWN

    entities: list[ExtractedEntity] = field(default_factory=list)

    keywords: list[str] = field(default_factory=list)