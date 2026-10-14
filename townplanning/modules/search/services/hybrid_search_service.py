from __future__ import annotations

import logging

from townplanning.core.settings import get_settings
from townplanning.modules.search.dom.search_result import (
    SearchResult,
)
from townplanning.modules.search.services.bm25_search_service import (
    BM25SearchService,
)
from townplanning.modules.search.services.rrf_service import (
    RRFService,
)
from townplanning.modules.search.services.semantic_search_service import (
    SemanticSearchService,
)

logger = logging.getLogger(__name__)


class HybridSearchService:
    """
    Hybrid Search Service.

    Combines:

    - Semantic Search (Vector Search)
    - BM25 / PostgreSQL Full-Text Search

    using Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        semantic_search: SemanticSearchService,
        bm25_search: BM25SearchService,
        rrf_service: RRFService,
    ) -> None:

        settings = get_settings()

        self.semantic_search = semantic_search
        self.bm25_search = bm25_search
        self.rrf_service = rrf_service

        self.top_k = settings.SEARCH_TOP_K

    def search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """
        Execute Hybrid Search.

        Parameters
        ----------
        query:
            User question.

        top_k:
            Optional maximum results.

        Returns
        -------
        list[SearchResult]
        """

        effective_top_k = top_k or self.top_k

        logger.info(
            "Executing Hybrid Search for query: %s",
            query,
        )

        ############################################################
        # Semantic Search
        ############################################################

        semantic_results = self.semantic_search.search(
            query=query,
            top_k=effective_top_k,
        )

        logger.info(
            "Semantic Search returned %d results.",
            len(semantic_results),
        )

        ############################################################
        # BM25 Search
        ############################################################

        bm25_results = self.bm25_search.search(
            query=query,
            top_k=effective_top_k,
        )

        logger.info(
            "BM25 Search returned %d results.",
            len(bm25_results),
        )

        ############################################################
        # Reciprocal Rank Fusion
        ############################################################

        fused_results = self.rrf_service.fuse(
            semantic_results,
            bm25_results,
            top_k=effective_top_k,
        )

        logger.info(
            "Hybrid Search returned %d fused results.",
            len(fused_results),
        )

        return fused_results