from __future__ import annotations

from townplanning.core.settings import get_settings

from townplanning.modules.embeddings.providers.base_provider import (
    BaseEmbeddingProvider,
)

from townplanning.modules.embeddings.providers.ollama_provider import (
    OllamaEmbeddingProvider,
)

from townplanning.modules.embeddings.providers.openai_provider import (
    OpenAIEmbeddingProvider,
)


class ProviderFactory:
    """
    Factory class for creating an Embedding provider
    based on configuration.
    """

    @staticmethod
    def create() -> BaseEmbeddingProvider:

        settings = get_settings()

        provider_name = settings.EMBEDDING_PROVIDER.lower()

        providers = {
            "ollama": OllamaEmbeddingProvider,
            "openai": OpenAIEmbeddingProvider,
        }

        provider_cls = providers.get(provider_name)

        if provider_cls is None:
            raise ValueError(
                f"Unsupported embedding provider '{provider_name}'. "
                f"Supported providers: {', '.join(providers.keys())}"
            )

        return provider_cls()