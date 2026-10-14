from __future__ import annotations

import logging

from townplanning.core.settings import get_settings

from townplanning.modules.reranking.providers.base_provider import (
    BaseRerankingProvider,
)
from townplanning.modules.search.dom.search_result import SearchResult

logger = logging.getLogger(__name__)


class RerankingService:
    """
    High-level reranking service.

    Responsibilities
    ----------------
    - Invoke the configured reranking provider.
    - Apply reranking score threshold.
    - Limit returned results.
    - Return SearchResult objects.
    """

    def __init__(
        self,
        provider: BaseRerankingProvider,
    ) -> None:

        settings = get_settings()

        self.provider = provider
        self.top_k = settings.RERANK_TOP_K
        self.min_score = settings.RERANK_MIN_SCORE

    ##################################################################
    # Public API
    ##################################################################

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
    ) -> list[SearchResult]:

        if not results:
            logger.debug("No search results to rerank.")
            return []

        logger.info(
            "Reranking %d semantic search results.",
            len(results),
        )

        reranked = self.provider.rerank(
            query=query,
            results=results,
            top_k=self.top_k,
        )

        reranked = [
            item
            for item in reranked
            if item.rerank_score >= self.min_score
        ]

        logger.info(
            "%d documents remained after reranking.",
            len(reranked),
        )

        return [
            item.result
            for item in reranked
        ]