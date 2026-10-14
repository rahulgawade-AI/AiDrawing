from __future__ import annotations

from townplanning.core.settings import get_settings

from townplanning.modules.search.dom.context import Context
from townplanning.modules.search.dom.search_result import SearchResult


class ContextBuilder:
    """
    Builds a clean context for the LLM.

    Responsibilities

    - Remove duplicate chunks
    - Respect context size limit
    - Format readable context
    """

    def __init__(self) -> None:

        settings = get_settings()

        self.max_chars = settings.MAX_CONTEXT_CHARS

    ####################################################################
    # Public API
    ####################################################################

    def build(
        self,
        results: list[SearchResult],
    ) -> Context:

        results = self._deduplicate(results)

        selected = self._truncate(results)

        text = self._format(selected)

        return Context(
            text=text,
            sources=selected,
            total_results=len(results),
        )

    ####################################################################
    # Private
    ####################################################################

    def _deduplicate(
        self,
        results: list[SearchResult],
    ) -> list[SearchResult]:

        seen: set[str] = set()

        unique: list[SearchResult] = []

        for result in results:

            text = result.text.strip()

            if text in seen:
                continue

            seen.add(text)

            unique.append(result)

        return unique

    def _truncate(
        self,
        results: list[SearchResult],
    ) -> list[SearchResult]:

        selected: list[SearchResult] = []

        total = 0

        for result in results:

            length = len(result.text)

            if total + length > self.max_chars:
                break

            selected.append(result)

            total += length

        return selected

    def _format(
        self,
        results: list[SearchResult],
    ) -> str:

        if not results:
            return ""

        blocks: list[str] = []

        for index, result in enumerate(results, start=1):

            blocks.append(
                f"""SOURCE {index}

{result.text.strip()}
"""
            )

        return "\n------------------------------------------------------------\n".join(
            blocks
        )