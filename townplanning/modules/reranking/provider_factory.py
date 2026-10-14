from __future__ import annotations

from townplanning.modules.reranking.config import RerankingConfig
from townplanning.modules.reranking.providers.noop_provider import (
    NoopRerankingProvider,
)
from townplanning.modules.reranking.providers.sentence_transformer_provider import (
    SentenceTransformerProvider,
)


class ProviderFactory:
    """
    Factory for reranking providers.
    """

    @staticmethod
    def create():

        return SentenceTransformerProvider(
            model_name=RerankingConfig.MODEL_NAME,
            device=RerankingConfig.DEVICE,
            batch_size=RerankingConfig.BATCH_SIZE,
        )

    @staticmethod
    def noop():

        return NoopRerankingProvider()