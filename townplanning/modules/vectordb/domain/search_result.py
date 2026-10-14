from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SearchResult:
    """
    Represents a single vector search result.
    """

    id: str

    text: str

    score: float

    metadata: dict[str, Any]