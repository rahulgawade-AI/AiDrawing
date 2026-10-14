from townplanning.modules.embeddings.providers.ollama_provider import (
    OllamaEmbeddingProvider,
)
from townplanning.modules.embeddings.services.embedding_service import (
    EmbeddingService,
)
from townplanning.modules.search.services.context_builder import (
    ContextBuilder,
)
from townplanning.modules.search.services.semantic_search_service import (
    SemanticSearchService,
)
from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)


def main():

    provider = OllamaEmbeddingProvider()

    embedding_service = EmbeddingService(provider)

    vectordb = ChromaRepository()

    search = SemanticSearchService(
        embedding_service,
        vectordb,
    )

    builder = ContextBuilder()

    query = "minimum staircase width"

    results = search.search(
        query=query,
        top_k=10,
    )

    context = builder.build(results)

    print("=" * 80)
    print("LLM CONTEXT")
    print("=" * 80)

    print(context.text)

    print("\n")

    print("=" * 80)
    print(f"Context Items : {len(context.items)}")
    print("=" * 80)


if __name__ == "__main__":
    main()