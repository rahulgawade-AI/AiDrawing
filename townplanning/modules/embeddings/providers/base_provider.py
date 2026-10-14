from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from townplanning.modules.embeddings.domain.embedding_request import (
    EmbeddingRequest,
)
from townplanning.modules.embeddings.domain.embedding_result import (
    EmbeddingResult,
)


class BaseEmbeddingProvider(ABC):
    """
    Base interface for embedding providers.
    """

    @abstractmethod
    def embed(
        self,
        requests: list[EmbeddingRequest],
    ) -> list[EmbeddingResult]:
        """
        Generate embeddings.
        """
        raise NotImplementedError