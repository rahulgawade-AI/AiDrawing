from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ChatResponse:
    """
    Raw response returned by an LLM provider.
    """

    content: str

    model: str

    prompt_tokens: int

    completion_tokens: int

    finish_reason: str