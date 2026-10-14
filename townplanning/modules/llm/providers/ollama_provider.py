from __future__ import annotations

import requests

from townplanning.core.settings import get_settings
from townplanning.modules.llm.domain.chat_request import ChatRequest
from townplanning.modules.llm.domain.chat_response import ChatResponse
from townplanning.modules.llm.providers.base_provider import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):

    def __init__(self):

        settings = get_settings()

        self.host = settings.OLLAMA_HOST.rstrip("/")

        self.model = settings.OLLAMA_MODEL

        self.timeout = settings.OLLAMA_TIMEOUT

    def generate(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        response = requests.post(

            f"{self.host}/api/chat",

            json={
                "model": self.model,
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                    }
                    for m in request.messages
                ],
                "stream": False,
            },

            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        return ChatResponse(

            content=data["message"]["content"],

            model=data["model"],

            prompt_tokens=0,

            completion_tokens=0,

            finish_reason="stop",
        )