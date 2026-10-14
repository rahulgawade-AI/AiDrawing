from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from townplanning.modules.retrieval.domain.source_type import SourceType


@dataclass(slots=True)
class Chunk:
    """
    A semantic chunk generated from a source document.

    Chunk objects are transient and are passed directly
    to the Embedding Service.
    """

    id: str

    source_type: SourceType

    source_id: UUID | str

    chunk_index: int

    title: str

    text: str

    page_number: int | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.text)

    def is_empty(self) -> bool:
        return not self.text.strip()