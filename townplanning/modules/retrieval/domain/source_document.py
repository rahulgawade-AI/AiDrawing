from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from .source_type import SourceType


@dataclass(slots=True)
class SourceDocument:
    """
    Generic document used by Chunking, Embeddings and RAG.
    """

    source_type: SourceType

    source_id: UUID | str

    title: str

    text: str

    page_number: int | None = None

    metadata: dict[str, Any] = field(default_factory=dict)