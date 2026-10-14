from __future__ import annotations

from dataclasses import dataclass

from townplanning.modules.search.dom.search_result import SearchResult


@dataclass(slots=True)
class Context:
    """
    Context passed to the LLM.
    """

    text: str

    sources: list[SearchResult]

    total_results: int