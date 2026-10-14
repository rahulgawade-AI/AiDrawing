from __future__ import annotations

import time

from townplanning.modules.llm.domain.chat_message import ChatMessage
from townplanning.modules.llm.domain.chat_request import ChatRequest
from townplanning.modules.llm.domain.llm_answer import LLMAnswer
from townplanning.modules.llm.domain.prompt import Prompt
from townplanning.modules.llm.providers.base_provider import BaseLLMProvider


class LLMService:

    def __init__(
        self,
        provider: BaseLLMProvider,
    ):

        self.provider = provider

    def generate(
        self,
        question: str,
        prompt: Prompt,
    ) -> LLMAnswer:

        start = time.perf_counter()

        request = ChatRequest(

            messages=[

                ChatMessage(
                    role="system",
                    content=prompt.system,
                ),

                ChatMessage(
                    role="user",
                    content=prompt.user,
                ),
            ]

        )

        response = self.provider.generate(
            request,
        )

        elapsed = time.perf_counter() - start

        return LLMAnswer(

            question=question,

            answer=response.content,

            model=response.model,

            prompt_tokens=response.prompt_tokens,

            completion_tokens=response.completion_tokens,

            finish_reason=response.finish_reason,

            execution_time=elapsed,
        )