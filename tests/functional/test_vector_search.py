from townplanning.modules.embeddings.domain.embedding_request import (
    EmbeddingRequest,
)
from townplanning.modules.embeddings.providers.openai_provider import (
    OpenAIEmbeddingProvider,
)
from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)


def main():

    provider = OpenAIEmbeddingProvider()

    repo = ChromaRepository()

    request = EmbeddingRequest(
        id="query",
        text="What is the minimum road width?",
        metadata={},
    )

    embedding = provider.embed([request])[0]

    results = repo.search(
        embedding=embedding.embedding,
        top_k=5,
    )

    print()

    print("=" * 80)

    for result in results:

        print("Score :", result.score)

        print("Metadata :", result.metadata)

        print(result.text)

        print("-" * 80)


if __name__ == "__main__":
    main()