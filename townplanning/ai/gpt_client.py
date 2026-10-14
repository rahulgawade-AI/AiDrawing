"""
Production OpenAI GPT Client.
"""

from openai import OpenAI

from townplanning.core.settings import get_settings

from .ai_client import AIClient
from .models import AIRequest, AIResponse


class GPTClient(AIClient):

    def __init__(self):

        settings = get_settings()

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

        self.model = settings.OPENAI_MODEL

    # --------------------------------------------------

    def generate(
        self,
        request: AIRequest,
    ) -> AIResponse:

        try:

            response = self.client.responses.create(

                model=self.model,

                input=[
                    {
                        "role": "system",
                        "content": request.system_prompt,
                    },
                    {
                        "role": "user",
                        "content": request.user_prompt,
                    },
                ],

                text={
                    "format": {
                        "type": "json_object",
                    }
                },
            )

            return AIResponse(

                success=True,

                content=response.output_text,

                raw_response=response,
            )

        except Exception as exc:

            return AIResponse(

                success=False,

                content="",

                raw_response=None,

                error=str(exc),
            )