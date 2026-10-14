from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Prompt:
    """
    Final prompt supplied to an LLM.
    """

    system: str

    user: str