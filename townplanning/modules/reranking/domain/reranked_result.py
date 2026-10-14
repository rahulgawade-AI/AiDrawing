from __future__ import annotations

from dataclasses import dataclass

from townplanning.modules.search.dom.search_result import SearchResult


@dataclass(slots=True)
class RerankedResult:
    """
    Search result after reranking.
    """

    result: SearchResult

    rerank_score: float