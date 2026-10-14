from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GenerationConfig:
    """
    Generation parameters shared by all providers.
    """

    temperature: float = 0.2

    max_tokens: int = 2000

    top_p: float = 1.0

    stream: bool = False