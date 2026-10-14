from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ChatMessage:
    """
    Single chat message exchanged with an LLM.
    """

    role: str

    content: str