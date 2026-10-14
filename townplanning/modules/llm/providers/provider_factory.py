from townplanning.core.settings import get_settings

from townplanning.modules.llm.providers.openai_provider import OpenAIProvider
from townplanning.modules.llm.providers.ollama_provider import OllamaProvider


class ProviderFactory:

    @staticmethod
    def create():

        settings = get_settings()

        provider = settings.AI_PROVIDER.lower()

        if provider == "openai":
            return OpenAIProvider()

        if provider == "ollama":
            return OllamaProvider()

        raise ValueError(
            f"Unsupported AI provider: {provider}"
        )