from __future__ import annotations

from townplanning.core.settings import get_settings

from townplanning.modules.embeddings.services.embedding_service import (
    EmbeddingService,
)
from townplanning.modules.search.dom.search_result import (
    SearchResult,
)
from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)


class SemanticSearchService:
    """
    Performs semantic search over the vector database.

    Responsibilities
    ----------------
    - Generate query embeddings
    - Retrieve candidate documents
    - Normalize scores
    - Filter low-confidence matches
    - Remove duplicates
    - Sort by relevance
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vectordb: ChromaRepository,
    ) -> None:

        settings = get_settings()

        self.embedding_service = embedding_service
        self.vectordb = vectordb

        self.top_k = settings.SEARCH_TOP_K
        self.max_results = settings.SEARCH_MAX_RESULTS
        self.min_score = settings.SEARCH_MIN_SCORE

    ####################################################################
    # Public API
    ####################################################################

    def search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """
        Perform semantic search.
        """

        effective_top_k = top_k or self.top_k

        # Generate embedding
        embedding = self._embed(query)

        # Retrieve candidate documents
        results = self._retrieve(
            embedding=embedding,
            top_k=effective_top_k,
        )

        # Normalize similarity scores
        results = self._normalize(results)

        # Remove weak matches
        results = self._filter(results)

        # Remove duplicate chunks
        results = self._deduplicate(results)

        # Sort by descending similarity
        results = self._sort(results)

        # Debug logging
        self._log_results(
            query=query,
            results=results,
        )

        # Limit returned results
        limit = top_k or self.max_results

        return results[:limit]

    ####################################################################
    # Private Methods
    ####################################################################

    def _embed(
        self,
        query: str,
    ) -> list[float]:
        """
        Generate query embedding.
        """

        return self.embedding_service.embed_query(query)

    def _retrieve(
        self,
        embedding: list[float],
        top_k: int,
    ) -> list[SearchResult]:
        """
        Retrieve candidate documents.
        """

        return self.vectordb.search(
            embedding=embedding,
            top_k=top_k,
        )

    def _normalize(
        self,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        """
        Normalize similarity scores.

        ChromaRepository already converts vector distances
        into similarity scores, so no additional work is
        currently required.
        """

        return results

    def _filter(
        self,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        """
        Remove weak matches.
        """

        return [
            result
            for result in results
            if result.score >= self.min_score
        ]

    def _deduplicate(
        self,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        """
        Remove duplicate search results.
        """

        seen: set[str] = set()
        unique: list[SearchResult] = []

        for result in results:

            if result.id in seen:
                continue

            seen.add(result.id)
            unique.append(result)

        return unique

    def _sort(
        self,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        """
        Sort by descending similarity score.
        """

        return sorted(
            results,
            key=lambda r: r.score,
            reverse=True,
        )

    ####################################################################
    # Debug
    ####################################################################

    def _log_results(
        self,
        query: str,
        results: list[SearchResult],
    ) -> None:

        print("\n" + "=" * 80)
        print("SEMANTIC SEARCH")
        print("=" * 80)

        print(f"Question : {query}")
        print(f"Retrieved: {len(results)}")

        if not results:
            print("No matching documents found.")
            print("=" * 80)
            return

        print("\nTop Matches")
        print("-" * 80)

        for index, result in enumerate(results[:5], start=1):

            preview = (
                result.text[:100]
                .replace("\n", " ")
                .strip()
            )

            print(
                f"{index:2d}. "
                f"Score={result.score:.3f} "
                f"| {preview}..."
            )

        print("=" * 80)