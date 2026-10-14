from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ContextItem:
    """
    Single context passed to the LLM.
    """

    id: str

    score: float

    text: str

    metadata: dict[str, Any]