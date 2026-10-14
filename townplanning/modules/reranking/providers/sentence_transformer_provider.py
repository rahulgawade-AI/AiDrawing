from __future__ import annotations

import logging
import threading

from sentence_transformers import CrossEncoder

from townplanning.modules.reranking.domain.reranked_result import (
    RerankedResult,
)
from townplanning.modules.reranking.providers.base_provider import (
    BaseRerankingProvider,
)
from townplanning.modules.search.dom.search_result import SearchResult

logger = logging.getLogger(__name__)


class SentenceTransformerProvider(BaseRerankingProvider):
    """
    Production CrossEncoder reranker.

    Features
    --------
    - Lazy model loading
    - Thread-safe singleton loading
    - CPU/GPU support
    - Batch inference
    - Stable sorting
    - Keeps original SearchResult
    """

    _model: CrossEncoder | None = None
    _lock = threading.Lock()

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        batch_size: int = 32,
    ) -> None:

        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size

    ##################################################################
    # Lazy Loader
    ##################################################################

    def _load_model(self) -> CrossEncoder:

        if self.__class__._model is None:

            with self.__class__._lock:

                if self.__class__._model is None:

                    logger.info(
                        "Loading reranker model '%s' on %s",
                        self.model_name,
                        self.device,
                    )

                    self.__class__._model = CrossEncoder(
                        self.model_name,
                        device=self.device,
                    )

                    logger.info("Reranker model loaded.")

        return self.__class__._model

    ##################################################################
    # Public API
    ##################################################################

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[RerankedResult]:

        if not results:
            return []

        model = self._load_model()

        pairs = [
            (query, result.text)
            for result in results
        ]

        logger.debug(
            "Reranking %d search results...",
            len(results),
        )

        scores = model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )

        reranked = [

            RerankedResult(
                result=result,
                rerank_score=float(score),
            )

            for result, score in zip(results, scores)

        ]

        reranked.sort(
            key=lambda item: item.rerank_score,
            reverse=True,
        )

        if top_k is not None:
            reranked = reranked[:top_k]

        return reranked