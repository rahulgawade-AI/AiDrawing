from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Prompt:
    """
    Prompt sent to an LLM.
    """

    system: str

    user: str