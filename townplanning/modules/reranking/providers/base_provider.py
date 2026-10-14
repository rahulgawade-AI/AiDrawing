from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from townplanning.modules.search.dom.search_result import SearchResult
from townplanning.modules.reranking.domain.reranked_result import (
    RerankedResult,
)


class BaseRerankingProvider(ABC):
    """
    Base interface for reranking providers.
    """

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[SearchResult],
    ) -> list[RerankedResult]:
        """
        Return results sorted by descending relevance.
        """
        raise NotImplementedError