from __future__ import annotations

import time

from townplanning.infrastructure.database.session import SessionLocal

from townplanning.infrastructure.database.repositories.sqlalchemy_ocr_repository import (
    SQLAlchemyOCRRepository,
)
from townplanning.infrastructure.database.repositories.regulation_repository import (
    SQLAlchemyRegulationRepository,
)
from townplanning.infrastructure.database.repositories.rule_repository import (
    SQLAlchemyRuleRepository,
)
from townplanning.infrastructure.database.repositories.table_repository import (
    SQLAlchemyTableRepository,
)
from townplanning.infrastructure.database.repositories.knowledge_repository import (
    SQLAlchemyKnowledgeRepository,
)

from townplanning.modules.retrieval.services.document_retrieval_service import (
    DocumentRetrievalService,
)

from townplanning.modules.chunking.services.chunking_service import (
    ChunkingService,
)

from townplanning.modules.embeddings.services.embedding_service import (
    EmbeddingService,
)

from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)

from townplanning.modules.vectordb.services.vector_ingestion_service import (
    VectorIngestionService,
)
from townplanning.modules.embeddings.providers.ollama_provider import (
    OllamaEmbeddingProvider,
)


def main():

    start = time.time()

    session = SessionLocal()
    provider = OllamaEmbeddingProvider()

    try:

        retrieval = DocumentRetrievalService(

            ocr_repository=SQLAlchemyOCRRepository(session),

            regulation_repository=SQLAlchemyRegulationRepository(session),

            rule_repository=SQLAlchemyRuleRepository(session),

            table_repository=SQLAlchemyTableRepository(session),

            knowledge_repository=SQLAlchemyKnowledgeRepository(session),

        )

        chunking = ChunkingService()

        embedding = EmbeddingService(provider=provider,)

        vector_repository = ChromaRepository()

        ingestion = VectorIngestionService(

            chunking_service=chunking,

            embedding_service=embedding,

            repository=vector_repository,

        )

        print("=" * 80)
        print("Loading documents...")
        print("=" * 80)

        documents = retrieval.get_all_documents()

        print(f"Found {len(documents)} documents\n")

        total_chunks = 0

        for index, document in enumerate(documents, start=1):

            chunks = ingestion.ingest(document)

            total_chunks += chunks

            print(
                f"[{index:5d}/{len(documents)}] "
                f"{document.source_type.name:<18}"
                f"{chunks:4d} chunks   "
                f"{document.title}"
            )

        print()

        print("=" * 80)
        print("Embedding Complete")
        print("=" * 80)

        print(f"Documents      : {len(documents)}")
        print(f"Chunks         : {total_chunks}")
        print(f"Vectors Stored : {vector_repository.count()}")
        print(f"Elapsed Time   : {time.time()-start:.2f} sec")

    finally:

        session.close()


if __name__ == "__main__":

    main()