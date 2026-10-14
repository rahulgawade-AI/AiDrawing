"""
AI Client Factory.
"""

from townplanning.core.settings import get_settings

from .gpt_client import GPTClient
from .ollama_client import OllamaClient


class AIClientFactory:

    @staticmethod
    def create():

        settings = get_settings()

        provider = settings.AI_PROVIDER.lower()

        if provider == "openai":

            return GPTClient()

        if provider == "ollama":

            return OllamaClient()

        raise ValueError(
            f"Unsupported AI provider: {provider}"
        )