"""
Production Ollama client.
"""

from __future__ import annotations

import requests

from townplanning.core.settings import get_settings

from .ai_client import AIClient
from .models import AIRequest
from .models import AIResponse


class OllamaClient(AIClient):

    def __init__(self):

        settings = get_settings()

        self.host = (
            settings.OLLAMA_HOST.rstrip("/")
        )

        self.model = settings.OLLAMA_MODEL

        self.timeout = (
            settings.OLLAMA_TIMEOUT
        )

    # --------------------------------------------------
    # Generate
    # --------------------------------------------------

    def generate(
        self,
        request: AIRequest,
    ) -> AIResponse:

        user_message = {
            "role": "user",
            "content": request.user_prompt,
        }

        #
        # Vision support.
        #
        # Ollama expects:
        #
        # "images": [
        #     "<base64 image>"
        # ]
        #
        if request.images:

            user_message["images"] = (
                request.images
            )

        payload = {

            "model": self.model,

            "messages": [

                {
                    "role": "system",
                    "content": request.system_prompt,
                },

                user_message,

            ],

            "stream": False,

            "format": request.response_format,

            "options": {

                "temperature": request.temperature,

                "num_ctx": 8192,

                "num_predict": 4096,

            },
        }

        try:

            response = requests.post(

                f"{self.host}/api/chat",

                json=payload,

                timeout=self.timeout,

            )

            response.raise_for_status()

            data = response.json()

            return AIResponse(

                success=True,

                content=data["message"]["content"],

                raw_response=data,

            )

        except Exception as exc:

            return AIResponse(

                success=False,

                content="",

                raw_response=None,

                error=str(exc),

            )