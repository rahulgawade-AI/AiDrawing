from __future__ import annotations

import logging

from townplanning.modules.search.dom.search_result import (
    SearchResult,
)

logger = logging.getLogger(__name__)


class RRFService:
    """
    Reciprocal Rank Fusion (RRF).

    Combines multiple ranked result lists into a single ranked list.

    Reference:
        Cormack, Clarke & Büttcher (2009)
        "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods"

    Score(document) = Σ 1 / (k + rank)
    """

    def __init__(
        self,
        k: int = 60,
    ) -> None:
        self.k = k

    def fuse(
        self,
        *result_sets: list[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """
        Fuse multiple ranked result lists.

        Parameters
        ----------
        result_sets:
            Ranked SearchResult lists.

        top_k:
            Optional maximum results.

        Returns
        -------
        list[SearchResult]
        """

        scores: dict[str, float] = {}

        documents: dict[str, SearchResult] = {}

        ############################################################
        # Compute RRF scores
        ############################################################

        for results in result_sets:

            for rank, result in enumerate(results, start=1):

                documents[result.id] = result

                scores[result.id] = (
                    scores.get(result.id, 0.0)
                    + (1.0 / (self.k + rank))
                )

        ############################################################
        # Sort by fused score
        ############################################################

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        fused_results: list[SearchResult] = []

        for document_id, score in ranked:

            document = documents[document_id]

            fused_results.append(
                SearchResult(
                    id=document.id,
                    score=score,
                    text=document.text,
                    metadata=document.metadata,
                )
            )

        ############################################################
        # Limit
        ############################################################

        if top_k is not None:
            fused_results = fused_results[:top_k]

        logger.info(
            "RRF fused %d result sets into %d results.",
            len(result_sets),
            len(fused_results),
        )

        return fused_results