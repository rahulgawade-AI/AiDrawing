from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RegulatorySource:
    """
    A source fragment supplied to the semantic regulatory extractor.

    This is evidence only. It is not an evaluated planning rule.
    """

    source_id: str
    text: str

    regulation_number: str | None = None
    page: int | None = None
    source_type: str = "unknown"

    table_id: str | None = None
    table_number: str | None = None
    table_title: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "text": self.text,
            "regulation_number": self.regulation_number,
            "page": self.page,
            "source_type": self.source_type,
            "table_id": self.table_id,
            "table_number": self.table_number,
            "table_title": self.table_title,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class RegulatoryContext:
    """
    Complete source context supplied to Ollama.

    The context may contain:
      - primary Chroma hits
      - related regulation chunks
      - related tables
      - neighbouring source material
      - cross-reference material
    """

    query: str

    sources: list[RegulatorySource] = field(default_factory=list)

    requested_fields: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def add_source(self, source: RegulatorySource) -> None:
        self.sources.append(source)

    def add_sources(self, sources: list[RegulatorySource]) -> None:
        self.sources.extend(sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "requested_fields": self.requested_fields,
            "sources": [
                source.to_dict()
                for source in self.sources
            ],
            "metadata": self.metadata,
        }
