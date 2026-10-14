from uuid import uuid4

from townplanning.modules.chunking.services.chunking_service import (
    ChunkingService,
)
from townplanning.modules.embeddings.providers.openai_provider import (
    OpenAIEmbeddingProvider,
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
from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)
from townplanning.modules.vectordb.services.vector_ingestion_service import (
    VectorIngestionService,
)


def main():

    document = SourceDocument(

        source_type=SourceType.REGULATION,

        source_id=uuid4(),

        title="Road Width Regulation",

        text="""
Minimum road width shall be 12 metres.

Every internal road shall provide
adequate drainage.

Commercial roads shall be 18 metres.
""",

        page_number=10,

        metadata={

            "document": "UDCPR",

            "chapter": "Roads",

            "regulation": "6.1",
        },
    )

    chunking = ChunkingService()

    provider = OpenAIEmbeddingProvider()

    embedding = EmbeddingService(provider)

    chroma = ChromaRepository()

    ingestion = VectorIngestionService(
        chunking_service=chunking,
        embedding_service=embedding,
        repository=chroma,
    )

    total = ingestion.ingest(document)

    print()

    print("=" * 60)

    print(f"Inserted {total} vectors")

    print("=" * 60)


if __name__ == "__main__":
    main()