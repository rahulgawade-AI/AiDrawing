from __future__ import annotations

from openai import OpenAI

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


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """
    OpenAI embedding provider.
    """

    #MODEL = "text-embedding-3-small"

    #BATCH_SIZE = 100

    #def __init__(self) -> None:

    #    self.client = OpenAI(
    #        api_key=settings.OPENAI_API_KEY,
    #    )

    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
        )

        self.model = settings.EMBEDDING_MODEL

        self.batch_size = settings.EMBEDDING_BATCH_SIZE

    def embed(
        self,
        requests: list[EmbeddingRequest],
    ) -> list[EmbeddingResult]:

        results: list[EmbeddingResult] = []

        for start in range(
            0,
            len(requests),
            self.batch_size,
        ):

            batch = requests[
                start:start + self.batch_size
            ]

            response = self.client.embeddings.create(
                model=self.model,
                input=[
                    request.text
                    for request in batch
                ],
            )

            for request, embedding in zip(
                batch,
                response.data,
            ):

                results.append(

                    EmbeddingResult(

                        id=request.id,

                        embedding=embedding.embedding,
                    )
                )

        return results