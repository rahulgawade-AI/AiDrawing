from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class EmbeddingRecord:
    """
    Record written to the vector database.
    """

    id: str

    text: str

    embedding: list[float]

    metadata: dict[str, Any]