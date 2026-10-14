from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EmbeddingResult:
    """
    Result returned by an embedding provider.
    """

    id: str

    embedding: list[float]