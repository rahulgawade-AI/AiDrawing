from __future__ import annotations

from townplanning.modules.citations.services.citation_service import (
    CitationService,
)
from townplanning.modules.llm.domain.llm_answer import (
    LLMAnswer,
)
from townplanning.modules.llm.services.llm_service import (
    LLMService,
)
from townplanning.modules.llm.services.prompt_builder import (
    PromptBuilder,
)
from townplanning.modules.query.services.query_processing_service import (
    QueryProcessingService,
)
from townplanning.modules.reranking.services.reranking_service import (
    RerankingService,
)
from townplanning.modules.search.services.context_builder import (
    ContextBuilder,
)
from townplanning.modules.search.services.hybrid_search_service import (
    HybridSearchService,
)

from townplanning.workflows.base_workflow import (
    BaseWorkflow,
)


class QuestionAnsweringWorkflow(BaseWorkflow):
    """
    Question Answering Workflow.

            Question
                │
                ▼
       Query Processing
                │
                ▼
         Hybrid Search
                │
                ▼
          Cross Encoder
                │
                ▼
        Context Builder
                │
                ▼
        Prompt Builder
                │
                ▼
          LLM Service
                │
                ▼
       Citation Service
                │
                ▼
           LLM Answer
    """

    def __init__(
        self,
        *,
        query_processing_service: QueryProcessingService,
        hybrid_search: HybridSearchService,
        reranking_service: RerankingService,
        context_builder: ContextBuilder,
        prompt_builder: PromptBuilder,
        llm_service: LLMService,
        citation_service: CitationService,
    ) -> None:

        self._query_processing = query_processing_service

        self._hybrid_search = hybrid_search

        self._reranking_service = reranking_service

        self._context_builder = context_builder

        self._prompt_builder = prompt_builder

        self._llm_service = llm_service

        self._citation_service = citation_service

    ####################################################################
    # Properties
    ####################################################################

    @property
    def query_processing_service(
        self,
    ) -> QueryProcessingService:
        """
        Exposed only for development/debugging.
        """

        return self._query_processing

    ####################################################################
    # Execute
    ####################################################################

    def execute(
        self,
        question: str,
    ) -> LLMAnswer:
        """
        Execute the complete Question Answering workflow.
        """

        ################################################################
        # Step 1 - Query Processing
        ################################################################

        query = self._query_processing.process(
            question,
        )

        ################################################################
        # Step 2 - Hybrid Search
        ################################################################

        search_results = self._hybrid_search.search(
            query=query.expanded,
        )

        ################################################################
        # Step 3 - Cross Encoder Reranking
        ################################################################

        search_results = self._reranking_service.rerank(
            query=question,
            results=search_results,
        )

        ################################################################
        # Step 4 - Context Builder
        ################################################################

        context = self._context_builder.build(
            search_results,
        )

        ################################################################
        # Step 5 - Prompt Builder
        ################################################################

        prompt = self._prompt_builder.build(
            query=query,
            context=context,
        )

        ################################################################
        # Step 6 - LLM
        ################################################################

        answer = self._llm_service.generate(
            question=question,
            prompt=prompt,
        )

        ################################################################
        # Step 7 - Citations
        ################################################################

        answer.citations = self._citation_service.build(
            search_results,
        )

        return answer

    ####################################################################
    # Convenience API
    ####################################################################

    def ask(
        self,
        question: str,
    ) -> LLMAnswer:
        """
        Convenience wrapper.
        """

        return self.execute(question)