from townplanning.modules.embeddings.services.embedding_service import (
    EmbeddingService,
)


from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)

from townplanning.modules.search.dom.search_result import (
    SearchResult,
)

class SemanticSearchService:
    """
    Semantic vector search service.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vectordb: ChromaRepository,
    ):
        self.embedding_service = embedding_service
        self.vectordb = vectordb

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[SearchResult]:

        embedding = self.embedding_service.embed_query(query)

        return self.vectordb.search(
            embedding=embedding,
            top_k=top_k,
        )