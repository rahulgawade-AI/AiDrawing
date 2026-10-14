from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from townplanning.modules.llm.domain.chat_request import ChatRequest
from townplanning.modules.llm.domain.chat_response import ChatResponse


class BaseLLMProvider(ABC):
    """
    Base interface for all LLM providers.
    """

    @abstractmethod
    def generate(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        ...