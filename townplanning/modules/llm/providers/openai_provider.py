from __future__ import annotations

from openai import OpenAI

from townplanning.core.settings import get_settings
from townplanning.modules.llm.domain.chat_request import ChatRequest
from townplanning.modules.llm.domain.chat_response import ChatResponse
from townplanning.modules.llm.providers.base_provider import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI GPT provider.
    """

    def __init__(self) -> None:

        settings = get_settings()

        self.model = settings.OPENAI_MODEL

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
        )

    def generate(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        response = self.client.chat.completions.create(

            model=self.model,

            messages=[
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in request.messages
            ],

            temperature=request.temperature,

            max_completion_tokens=request.max_tokens,
        )

        choice = response.choices[0]

        usage = response.usage

        return ChatResponse(

            content=choice.message.content,

            model=response.model,

            prompt_tokens=usage.prompt_tokens,

            completion_tokens=usage.completion_tokens,

            finish_reason=choice.finish_reason,
        )