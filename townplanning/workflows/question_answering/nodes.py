from __future__ import annotations

from dataclasses import replace

from .state import QuestionAnsweringState

from townplanning.modules.query.services.query_processing_service import (
    QueryProcessingService,
)
from townplanning.modules.search.services.hybrid_search_service import (
    HybridSearchService,
)
from townplanning.modules.reranking.services.reranking_service import (
    RerankingService,
)
from townplanning.modules.search.services.context_builder import (
    ContextBuilder,
)
from townplanning.modules.llm.services.prompt_builder import (
    PromptBuilder,
)
from townplanning.modules.llm.services.llm_service import (
    LLMService,
)
from townplanning.modules.citations.services.citation_service import(
    CitationService
)

from townplanning.modules.memory.services.memory_service import (
    MemoryService,
)

from townplanning.modules.memory.services.query_rewrite_service import (
    QueryRewriteService,
)

class QuestionAnsweringNodes:

    def __init__(
        self,
        query_processing_service: QueryProcessingService,
        hybrid_search_service: HybridSearchService,
        reranking_service: RerankingService,
        context_builder_service: ContextBuilder,
        prompt_builder: PromptBuilder,
        llm_service: LLMService,
        citation_service: CitationService,
        memory_service: MemoryService,
        query_rewrite_service: QueryRewriteService


    ):
        self.query_processing = query_processing_service
        self.hybrid_search = hybrid_search_service
        self.reranking = reranking_service
        self.context_builder = context_builder_service
        self.prompt_builder = prompt_builder
        self.llm = llm_service
        self.citation = citation_service
        self.memory = memory_service
        self.query_rewriter = query_rewrite_service


    def query_processing_node(
    self,
    state: QuestionAnsweringState,
    ) -> QuestionAnsweringState:
        """
        Process the user's query after conversational rewriting.
        """

        # Default to the original question
        question = state.question

        # Use the rewritten query if available
        if (
            state.conversation.rewritten_query is not None
            and state.conversation.rewritten_query.was_rewritten
        ):
            question = (
                state.conversation.rewritten_query.rewritten
            )

        state.query = self.query_processing.process(
            question
        )

        return state

    def hybrid_search_node(
    self,
        state: QuestionAnsweringState,
    ) -> QuestionAnsweringState:

        results = self.hybrid_search.search(
            query=state.query.expanded,
        )

        state.search_results = results

        return state

    
    def reranking_node(
    self,
    state: QuestionAnsweringState,
) -> QuestionAnsweringState:

        reranked = self.reranking.rerank(
            query=state.query.original,
            results=state.search_results,
        )

        state.search_results = reranked

        return state

    def context_builder_node(
        self,
        state: QuestionAnsweringState,
    ) -> QuestionAnsweringState:

        context = self.context_builder.build(
            state.search_results,
        )

        state.context = context

        return state

    def prompt_builder_node(
    self,
    state: QuestionAnsweringState,
    ) -> QuestionAnsweringState:

        prompt = self.prompt_builder.build(
    query=state.query,
    context=state.context,
    history=state.conversation.messages,
)

        state.prompt = prompt

        return state

    def load_memory_node(
        self,
        state: QuestionAnsweringState,
    ) -> QuestionAnsweringState:

       

       
        conversation = self.memory.get_or_create_conversation(
            state.conversation.conversation_id,
        )

        state.conversation.conversation_id = conversation.id

        state.conversation.messages = self.memory.load_history(
            conversation.id,
            )

        return state


    def llm_node(
        self,
        state: QuestionAnsweringState,
        ) -> QuestionAnsweringState:

        try:

            state.answer = self.llm.generate(
                question=state.question,
                prompt=state.prompt,
            )

        except Exception as exc:

            state.error = str(exc)

        return state

    
    def citation_node(
    self,
    state: QuestionAnsweringState,
    ) -> QuestionAnsweringState:

        state.citations = self.citation.build(
        results=state.search_results,
        )

        return state


    # def merge_memory_node(
    #     self,
    #     state: QuestionAnsweringState,
    # ) -> QuestionAnsweringState:

    #     if not state.history:

    #         return state

    #     history = []

    #     for message in state.history[-10:]:

    #         history.append(
    #             f"{message.role}: {message.message}"
    #         )

    #     state.context.text = (
    #         "Conversation History\n"
    #         "====================\n"
    #         + "\n".join(history)
    #         + "\n\nRetrieved Context\n"
    #         "=================\n"
    #         + state.context.text
    #     )

    #     return state


    def save_memory_node(
        self,
        state: QuestionAnsweringState,
    ) -> QuestionAnsweringState:

        self.memory.append_interaction(

            conversation_id=state.conversation.conversation_id,

            question=state.question,

            answer=state.answer.answer,

        )

        return state

    def query_rewrite_node(
        self,
        state: QuestionAnsweringState,
    ) -> QuestionAnsweringState:

        rewritten = self.query_rewriter.rewrite(

            question=state.question,

            history=state.conversation.messages,

        )

        state.conversation.rewritten_query = rewritten

        return state