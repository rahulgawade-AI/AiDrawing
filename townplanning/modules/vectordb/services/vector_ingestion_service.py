from __future__ import annotations

from townplanning.modules.chunking.domain.chunk import Chunk
from townplanning.modules.chunking.services.chunking_service import (
    ChunkingService,
)
from townplanning.modules.embeddings.services.embedding_service import (
    EmbeddingService,
)
from townplanning.modules.retrieval.domain.source_document import (
    SourceDocument,
)
from townplanning.modules.retrieval.domain.source_type import (
    SourceType,
)
from townplanning.modules.vectordb.repositories.base_repository import (
    BaseVectorRepository,
)


class VectorIngestionService:
    """
    Complete ingestion pipeline.

    Large Documents
        SourceDocument
              ↓
          Chunking
              ↓
         Embeddings
              ↓
          ChromaDB

    Atomic Documents
        SourceDocument
              ↓
       Single Chunk
              ↓
         Embeddings
              ↓
          ChromaDB
    """

    CHUNKED_SOURCE_TYPES = {
        SourceType.OCR,
        SourceType.REGULATION,
    }

    def __init__(
        self,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        repository: BaseVectorRepository,
    ) -> None:

        self.chunking = chunking_service
        self.embedding = embedding_service
        self.repository = repository

    def ingest(
        self,
        document: SourceDocument,
    ) -> int:

        if document.source_type in self.CHUNKED_SOURCE_TYPES:

            chunks = self.chunking.chunk_document(
                document,
            )

        else:

            chunks = [
                Chunk(
                    id=f"{document.source_type.name}:{document.source_id}",
                    source_type=document.source_type,
                    source_id=document.source_id,
                    chunk_index=0,
                    title=document.title,
                    text=document.text,
                    page_number=document.page_number,
                    metadata=document.metadata,
                )
            ]

        if not chunks:
            return 0

        records = self.embedding.embed_chunks(chunks)

        self.repository.add(records)

        return len(records)