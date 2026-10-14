from townplanning.modules.embeddings.providers.ollama_provider import (
    OllamaEmbeddingProvider,
)
from townplanning.modules.embeddings.services.embedding_service import (
    EmbeddingService,
)
from townplanning.modules.search.services.context_builder import (
    ContextBuilder,
)
from townplanning.modules.search.services.prompt_builder import (
    PromptBuilder,
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

    prompt_builder = PromptBuilder()

    question = "What is FSI?"

    results = search.search(
        query=question,
        top_k=10,
    )

    context = builder.build(results)

    prompt = prompt_builder.build(
        question=question,
        context=context,
    )

    print("=" * 80)
    print("SYSTEM PROMPT")
    print("=" * 80)
    print(prompt.system)

    print("\n")

    print("=" * 80)
    print("USER PROMPT")
    print("=" * 80)
    print(prompt.user)


if __name__ == "__main__":
    main()