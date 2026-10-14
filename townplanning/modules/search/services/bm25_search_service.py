from __future__ import annotations

import logging

from townplanning.core.settings import get_settings
from townplanning.modules.search.dom.search_result import (
    SearchResult,
)
from townplanning.modules.search.repositories.postgres_search_repository import (
    PostgresSearchRepository,
)

logger = logging.getLogger(__name__)


class BM25SearchService:
    """
    BM25 / PostgreSQL Full-Text Search service.

    Responsibilities
    ----------------
    - Execute keyword search.
    - Filter low-scoring results.
    - Return the highest ranked SearchResult objects.
    """

    def __init__(
        self,
        repository: PostgresSearchRepository,
    ) -> None:

        settings = get_settings()

        self.repository = repository

        self.top_k = settings.SEARCH_TOP_K

        self.max_results = settings.SEARCH_MAX_RESULTS

        self.min_score = settings.SEARCH_MIN_SCORE

    def search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """
        Execute a BM25 search.

        Parameters
        ----------
        query:
            User question.

        top_k:
            Optional override.

        Returns
        -------
        list[SearchResult]
        """

        effective_top_k = top_k or self.top_k

        logger.info(
            "Executing BM25 search for: %s",
            query,
        )

        results = self.repository.search(
            query=query,
            top_k=effective_top_k,
        )

        ############################################################
        # Filter by score
        ############################################################

        results = [
            result
            for result in results
            if result.score >= self.min_score
        ]

        ############################################################
        # Sort
        ############################################################

        results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        ############################################################
        # Limit
        ############################################################

        limit = top_k or self.max_results

        results = results[:limit]

        logger.info(
            "BM25 search returned %d filtered results.",
            len(results),
        )

        return results