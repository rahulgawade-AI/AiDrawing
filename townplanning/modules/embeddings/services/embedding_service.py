from __future__ import annotations

from townplanning.modules.chunking.domain.chunk import Chunk
from townplanning.modules.embeddings.domain.embedding_record import (
    EmbeddingRecord,
)
from townplanning.modules.embeddings.domain.embedding_request import (
    EmbeddingRequest,
)
from townplanning.modules.embeddings.providers.base_provider import (
    BaseEmbeddingProvider,
)

from townplanning.modules.embeddings.domain.embedding_request import (
    EmbeddingRequest,
)


class EmbeddingService:
    """
    Converts chunks into embedding records.
    """

    def __init__(
        self,
        provider: BaseEmbeddingProvider,
    ) -> None:

        self.provider = provider

    def embed_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[EmbeddingRecord]:

        requests = [

            EmbeddingRequest.from_chunk(
                chunk,
            )

            for chunk in chunks
        ]

        results = self.provider.embed(
            requests,
        )

        result_map = {

            result.id: result

            for result in results
        }

        records: list[EmbeddingRecord] = []

        for chunk in chunks:

            embedding = result_map[
                chunk.id
            ]

            records.append(

                EmbeddingRecord(

                    id=chunk.id,

                    text=chunk.text,

                    embedding=embedding.embedding,

                    metadata=chunk.metadata,
                )
            )

        return records

    def embed_query(
        self,
        query: str,
        ) -> list[float]:
        """
        Generate embedding for a user query.
        """
    
        request = EmbeddingRequest(
            id="query",
            text=query,
            metadata={},
        )
    
        result = self.provider.embed([request])[0]
    
        return result.embedding