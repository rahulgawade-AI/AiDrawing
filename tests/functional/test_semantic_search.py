from townplanning.modules.embeddings.providers.ollama_provider import (
    OllamaEmbeddingProvider,
)
from townplanning.modules.embeddings.services.embedding_service import (
    EmbeddingService,
)
from townplanning.modules.search.services.semantic_search_service import (
    SemanticSearchService,
)
from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)


def print_results(query, results):
    print("\n" + "=" * 100)
    print(f"QUERY : {query}")
    print("=" * 100)

    if not results:
        print("No results found.")
        return

    for i, result in enumerate(results, start=1):
        print(f"\nResult #{i}")
        print("-" * 80)
        print(f"Score       : {result.score:.4f}")
        print(f"ID          : {result.id}")

        metadata = result.metadata or {}

        print(f"Source Type : {metadata.get('source_type')}")
        print(f"Source ID   : {metadata.get('source_id')}")
        print(f"Page        : {metadata.get('page_number')}")

        print("\nText:")
        print(result.text[:600])
        print()


def main():

    provider = OllamaEmbeddingProvider()

    embedding_service = EmbeddingService(provider)

    vectordb = ChromaRepository()

    search_service = SemanticSearchService(
        embedding_service=embedding_service,
        vectordb=vectordb,
    )

    queries = [
        "minimum front setback",
        "FSI calculation",
        "occupation certificate",
        "parking requirements",
        "building height",
        "staircase width",
        "agro tourism",
        "road width",
    ]

    for query in queries:
        try:
            results = search_service.search(
                query=query,
                top_k=5,
            )

            print_results(query, results)

        except Exception as e:
            print(f"\nSearch failed for '{query}'")
            print(e)


if __name__ == "__main__":
    main()