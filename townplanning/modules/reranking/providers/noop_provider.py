from __future__ import annotations

from townplanning.modules.reranking.domain.reranked_result import (
    RerankedResult,
)
from townplanning.modules.reranking.providers.base_provider import (
    BaseRerankingProvider,
)
from townplanning.modules.search.dom.search_result import SearchResult


class NoopRerankingProvider(BaseRerankingProvider):

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
    ) -> list[RerankedResult]:

        return [
            RerankedResult(
                result=result,
                rerank_score=result.score,
            )
            for result in results
        ]