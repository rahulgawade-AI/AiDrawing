from __future__ import annotations

from typing import Any

import requests

from townplanning.core.settings import get_settings
from townplanning.modules.embeddings.domain.embedding_request import (
    EmbeddingRequest,
)
from townplanning.modules.embeddings.domain.embedding_result import (
    EmbeddingResult,
)
from townplanning.modules.embeddings.providers.base_provider import (
    BaseEmbeddingProvider,
)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """
    Ollama embedding provider.

    Uses the Ollama /api/embed endpoint.

    Recommended embedding models:

        - nomic-embed-text
        - mxbai-embed-large
        - bge-m3

    Example:

        OLLAMA_HOST=http://localhost:11434
        EMBEDDING_MODEL=nomic-embed-text
    """

    def __init__(self) -> None:

        settings = get_settings()

        self.host = settings.OLLAMA_HOST.rstrip("/")

        self.model = settings.EMBEDDING_MODEL

        self.batch_size = settings.EMBEDDING_BATCH_SIZE

        self.timeout = settings.OLLAMA_TIMEOUT

    def embed(
        self,
        requests_: list[EmbeddingRequest],
    ) -> list[EmbeddingResult]:

        if not requests_:
            return []

        results: list[EmbeddingResult] = []

        for start in range(
            0,
            len(requests_),
            self.batch_size,
        ):

            batch = requests_[start:start + self.batch_size]

            response = requests.post(
                f"{self.host}/api/embed",
                json={
                    "model": self.model,
                    "input": [
                        request.text
                        for request in batch
                    ],
                },
                timeout=self.timeout,
            )

            response.raise_for_status()

            data: dict[str, Any] = response.json()

            embeddings = data.get("embeddings")

            if embeddings is None:

                raise RuntimeError(
                    "Ollama did not return embeddings."
                )

            if len(embeddings) != len(batch):

                raise RuntimeError(
                    "Embedding count does not match request count."
                )

            for request, embedding in zip(
                batch,
                embeddings,
            ):

                results.append(
                    EmbeddingResult(
                        id=request.id,
                        embedding=embedding,
                    )
                )

        return results