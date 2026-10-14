from __future__ import annotations

from dataclasses import dataclass, field

from townplanning.modules.llm.domain.chat_message import ChatMessage


@dataclass(slots=True)
class ChatRequest:
    """
    Request sent to an LLM provider.
    """

    messages: list[ChatMessage]

    temperature: float = 0.2

    max_tokens: int = 2000

    stream: bool = False