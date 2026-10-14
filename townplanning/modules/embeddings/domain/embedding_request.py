from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from townplanning.modules.chunking.domain.chunk import Chunk


@dataclass(slots=True)
class EmbeddingRequest:
    """
    Request sent to an embedding provider.
    """

    id: str

    text: str

    metadata: dict[str, Any]

    @classmethod
    def from_chunk(
        cls,
        chunk: Chunk,
    ) -> "EmbeddingRequest":

        return cls(
            id=chunk.id,
            text=chunk.text,
            metadata=chunk.metadata,
        )