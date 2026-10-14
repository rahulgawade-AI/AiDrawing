from __future__ import annotations

from townplanning.modules.embeddings.providers.ollama_provider import (
    OllamaEmbeddingProvider,
)
from townplanning.modules.embeddings.services.embedding_service import (
    EmbeddingService,
)

from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)

from townplanning.modules.search.services.semantic_search_service import (
    SemanticSearchService,
)
from townplanning.modules.search.services.context_builder import (
    ContextBuilder,
)

from townplanning.modules.reranking.provider_factory import (
    ProviderFactory as RerankingProviderFactory,
)
from townplanning.modules.reranking.services.reranking_service import (
    RerankingService,
)

from townplanning.modules.llm.providers.provider_factory import (
    ProviderFactory,
)
from townplanning.modules.llm.services.llm_service import (
    LLMService,
)
from townplanning.modules.llm.services.prompt_builder import (
    PromptBuilder,
)

from townplanning.modules.citations.services.citation_service import (
    CitationService,
)

from townplanning.workflows.question_answering_workflow import (
    QuestionAnsweringWorkflow,
)

from townplanning.modules.search.repositories.postgres_search_repository import (
    PostgresSearchRepository,
)

from townplanning.modules.search.services.bm25_search_service import (
    BM25SearchService,
)

from townplanning.modules.search.services.hybrid_search_service import (
    HybridSearchService,
)

from townplanning.modules.search.services.rrf_service import (
    RRFService,
)

from townplanning.modules.query.services.acronym_service import (
    AcronymService,
)

from townplanning.modules.query.services.synonym_service import (
    SynonymService,
)

from townplanning.modules.query.services.query_expansion_service import (
    QueryExpansionService,
)

from townplanning.modules.query.services.intent_detection_service import (
    IntentDetectionService,
)

from townplanning.modules.query.services.entity_extraction_service import (
    EntityExtractionService,
)

from townplanning.modules.query.services.query_processing_service import (
    QueryProcessingService,
)

def build_workflow() -> QuestionAnsweringWorkflow:
    """
    Build the complete Question Answering workflow.
    """

    ####################################################################
    # Embeddings
    ####################################################################

    embedding_provider = OllamaEmbeddingProvider()

    embedding_service = EmbeddingService(
        provider=embedding_provider,
    )

    ####################################################################
    # Vector Database
    ####################################################################

    vectordb = ChromaRepository()

    ####################################################################
    # Semantic Search
    ####################################################################

    semantic_search = SemanticSearchService(
        embedding_service=embedding_service,
        vectordb=vectordb,
    )

        ####################################################################
    # PostgreSQL BM25 Search
    ####################################################################

    postgres_repository = PostgresSearchRepository()

    bm25_search = BM25SearchService(
        repository=postgres_repository,
    )
        ####################################################################
    # Reciprocal Rank Fusion
    ####################################################################

    rrf_service = RRFService()

        ####################################################################
    # Hybrid Search
    ####################################################################

    hybrid_search = HybridSearchService(
        semantic_search=semantic_search,
        bm25_search=bm25_search,
        rrf_service=rrf_service,
    )


    ####################################################################
    # Query Processing
    ####################################################################

    acronym_service = AcronymService()

    synonym_service = SynonymService()

    query_expansion_service = QueryExpansionService(
        acronym_service=acronym_service,
        synonym_service=synonym_service,
    )

    intent_detection_service = IntentDetectionService()

    entity_extraction_service = EntityExtractionService()

    query_processing_service = QueryProcessingService(
        intent_detection_service=intent_detection_service,
        entity_extraction_service=entity_extraction_service,
        query_expansion_service=query_expansion_service,
    )


    ####################################################################
    # Reranking
    ####################################################################

    reranking_service = RerankingService(
        provider=RerankingProviderFactory.create(),
    )

    ####################################################################
    # Context Builder
    ####################################################################

    context_builder = ContextBuilder()

    ####################################################################
    # Prompt Builder
    ####################################################################

    prompt_builder = PromptBuilder()

    ####################################################################
    # LLM
    ####################################################################

    llm_service = LLMService(
        provider=ProviderFactory.create(),
    )

    ####################################################################
    # Citation Service
    ####################################################################

    citation_service = CitationService()

    ####################################################################
    # Workflow
    ####################################################################

    return QuestionAnsweringWorkflow(
        query_processing_service=query_processing_service,
        hybrid_search=hybrid_search,
        reranking_service=reranking_service,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        llm_service=llm_service,
        citation_service=citation_service,
)


def print_citations(answer) -> None:
    """
    Pretty-print citations.
    """

    print("\n")
    print("=" * 100)
    print("CITATIONS")
    print("=" * 100)

    if not answer.citations:
        print("No citations available.")
        return

    for citation in answer.citations:

        print(f"[{citation.number}] {citation.source}")

        if citation.title:
            print(f"    Title : {citation.title}")

        if citation.page:
            print(f"    Page  : {citation.page}")

        if citation.metadata:

            metadata = citation.metadata

            if metadata.get("section"):
                print(f"    Section    : {metadata['section']}")

            if metadata.get("chapter"):
                print(f"    Chapter    : {metadata['chapter']}")

            if metadata.get("regulation"):
                print(f"    Regulation : {metadata['regulation']}")

            if metadata.get("rule"):
                print(f"    Rule       : {metadata['rule']}")

            if metadata.get("clause"):
                print(f"    Clause     : {metadata['clause']}")

            if metadata.get("document"):
                print(f"    Document   : {metadata['document']}")


def print_query(query) -> None:

    print("\n")
    print("=" * 100)
    print("QUERY ANALYSIS")
    print("=" * 100)

    print(f"Original   : {query.original}")
    print(f"Normalized : {query.normalized}")
    print(f"Expanded   : {query.expanded}")
    print(f"Intent     : {query.intent.name}")

    print("\nEntities")

    if not query.entities:
        print("  None")
    else:
        for entity in query.entities:
            print(f"  {entity.entity_type:20} {entity.value}")

    print("\nKeywords")

    if not query.keywords:
        print("  None")
    else:
        for keyword in query.keywords:
            print(f"  {keyword}")


def main():

    print("=" * 80)
    print("AI Town Planning Assistant")
    print("=" * 80)

    workflow = build_workflow()

    while True:

        question = input("\nQuestion (exit to quit): ").strip()

        if question.lower() in {"exit", "quit"}:
            break

        if not question:
            continue

        print("\nSearching regulations...\n")

        try:

            query = workflow.query_processing_service.process(
            question,
            )

            print_query(query)

            answer = workflow.ask(question)

            print("=" * 100)
            print("ANSWER")
            print("=" * 100)

            print(answer.answer)

            print_citations(answer)

        except Exception as ex:

            print("\nERROR")
            print("-" * 80)
            print(type(ex).__name__)
            print(ex)


if __name__ == "__main__":
    main()