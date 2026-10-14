from townplanning.modules.embeddings.providers.provider_factory import (
    ProviderFactory,
)
from townplanning.modules.embeddings.services.embedding_service import (
    EmbeddingService,
)

from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)

from townplanning.modules.search.repositories.postgres_search_repository import (
    PostgresSearchRepository,
)

from townplanning.modules.search.services.semantic_search_service import (
    SemanticSearchService,
)
from townplanning.modules.search.services.bm25_search_service import (
    BM25SearchService,
)
from townplanning.modules.search.services.rrf_service import (
    RRFService,
)
from townplanning.modules.search.services.hybrid_search_service import (
    HybridSearchService,
)
from townplanning.modules.search.services.context_builder import (
    ContextBuilder,
)

from townplanning.modules.query.services.intent_detection_service import (
    IntentDetectionService,
)
from townplanning.modules.query.services.entity_extraction_service import (
    EntityExtractionService,
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
from townplanning.modules.query.services.query_processing_service import (
    QueryProcessingService,
)

from townplanning.modules.reranking.provider_factory import (
    ProviderFactory as RerankingProviderFactory,
)
from townplanning.modules.reranking.services.reranking_service import (
    RerankingService,
)

from townplanning.modules.citations.services.citation_service import (
    CitationService,
)

from townplanning.modules.llm.providers.provider_factory import (
    ProviderFactory as LLMProviderFactory,
)
from townplanning.modules.llm.services.llm_service import (
    LLMService,
)
from townplanning.modules.llm.services.prompt_builder import (
    PromptBuilder,
)

from townplanning.workflows.question_answering_workflow import (
    QuestionAnsweringWorkflow,
)

from townplanning.modules.memory.repositories.postgres_memory_repository import(
    PostgresMemoryRepository,
)

from townplanning.modules.memory.services.memory_service import(
    MemoryService
)

from townplanning.modules.memory.services.query_rewrite_service import (
    QueryRewriteService,
)

class ApplicationContainer:
    """
    Dependency Injection Container
    """

    ####################################################################
    # Embeddings
    ####################################################################

    def embedding_service(self):

        provider = ProviderFactory.create()

        return EmbeddingService(provider)

    ####################################################################
    # Vector DB
    ####################################################################

    def chroma_repository(self):

        return ChromaRepository()

    ####################################################################
    # PostgreSQL
    ####################################################################

    def postgres_repository(self):

        return PostgresSearchRepository()

    ####################################################################
    # Search
    ####################################################################

    def semantic_search_service(self):

        return SemanticSearchService(
            embedding_service=self.embedding_service(),
            vectordb=self.chroma_repository(),
        )

    def bm25_search_service(self):

        return BM25SearchService(
            repository=self.postgres_repository(),
        )

    def rrf_service(self):

        return RRFService()

    def hybrid_search_service(self):

        return HybridSearchService(
            semantic_search=self.semantic_search_service(),
            bm25_search=self.bm25_search_service(),
            rrf_service=self.rrf_service(),
        )

    ####################################################################
    # Query Processing
    ####################################################################

    def query_processing_service(self):

        expansion = QueryExpansionService(
            acronym_service=AcronymService(),
            synonym_service=SynonymService(),
        )

        return QueryProcessingService(
            intent_detection_service=IntentDetectionService(),
            entity_extraction_service=EntityExtractionService(),
            query_expansion_service=expansion,
        )

    ####################################################################
    # Reranking
    ####################################################################

    def reranking_service(self):

        provider = RerankingProviderFactory.create()

        return RerankingService(provider)

    ####################################################################
    # Context
    ####################################################################

    def context_builder(self):

        return ContextBuilder()

    ####################################################################
    # Prompt
    ####################################################################

    def prompt_builder(self):

        return PromptBuilder()

    ####################################################################
    # LLM
    ####################################################################

    def llm_service(self):

        provider = LLMProviderFactory.create()

        return LLMService(provider)

    ####################################################################
    # Citations
    ####################################################################

    def citation_service(self):

        return CitationService()

    ####################################################################
    # Memory Repository
    ####################################################################

    def memory_repository(self):

        return PostgresMemoryRepository()

    ####################################################################
    # Memory service
    ####################################################################

    def memory_service(self):
        return MemoryService( repository=self.memory_repository(),)

    def query_rewrite_service(self):

        return QueryRewriteService()
    

    ####################################################################
    # Workflow
    ####################################################################

    def question_answering_workflow(self):

        return QuestionAnsweringWorkflow(
            query_processing_service=self.query_processing_service(),
            hybrid_search=self.hybrid_search_service(),
            reranking_service=self.reranking_service(),
            context_builder=self.context_builder(),
            prompt_builder=self.prompt_builder(),
            llm_service=self.llm_service(),
            citation_service=self.citation_service(),
            memory_service=self.memory_service(),
            query_rewrite_service = self.query_rewrite_service(),
        )