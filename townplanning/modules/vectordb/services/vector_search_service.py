from __future__ import annotations

from townplanning.modules.embeddings.domain.embedding_request import (
    EmbeddingRequest,
)
from townplanning.modules.embeddings.providers.base_provider import (
    BaseEmbeddingProvider,
)
from townplanning.modules.vectordb.domain.search_result import (
    SearchResult,
)
from townplanning.modules.vectordb.repositories.base_repository import (
    BaseVectorRepository,
)


class VectorSearchService:
    """
    Performs semantic vector search.

    Workflow

    Question
        ↓
    OpenAI Embedding
        ↓
    Chroma Search
        ↓
    SearchResult
    """

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        repository: BaseVectorRepository,
    ) -> None:

        self.embedding_provider = embedding_provider

        self.repository = repository

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:

        request = EmbeddingRequest(
            id="query",
            text=query,
            metadata={},
        )

        embedding = self.embedding_provider.embed(
            [request]
        )[0]

        return self.repository.search(
            embedding=embedding.embedding,
            top_k=top_k,
            filters=filters,
        )