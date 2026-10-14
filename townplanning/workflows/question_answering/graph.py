from __future__ import annotations

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

from townplanning.workflows.common.graph_factory import GraphFactory
from townplanning.workflows.question_answering.nodes import (
    QuestionAnsweringNodes,
)
from townplanning.workflows.question_answering.state import (
    QuestionAnsweringState,
)


class QuestionAnsweringGraph:
    """
    Builds the LangGraph workflow for Question Answering.
    """

    def __init__(
        self,
        nodes: QuestionAnsweringNodes,
    ):
        self._nodes = nodes

    def build(self):

        builder = StateGraph(QuestionAnsweringState)

        # ------------------------------------------------------------------
        # Nodes
        # ------------------------------------------------------------------

        builder.add_node(
            "query_processing",
            self._nodes.query_processing_node,
        )

        builder.add_node(
            "hybrid_search",
            self._nodes.hybrid_search_node,
        )

        builder.add_node(
            "reranking",
            self._nodes.reranking_node,
        )

        builder.add_node(
            "context_builder",
            self._nodes.context_builder_node,
        )

        builder.add_node(
            "prompt_builder",
            self._nodes.prompt_builder_node,
        )

        builder.add_node(
            "llm",
            self._nodes.llm_node,
        )

        builder.add_node(
            "citation",
            self._nodes.citation_node,
        )

        builder.add_node(
        "load_memory",
        self._nodes.load_memory_node,
        )

        

        builder.add_node(
            "save_memory",
        self._nodes.save_memory_node,
        )

        builder.add_node(
                    "query_rewrite",
                self._nodes.query_rewrite_node,
                )

        # ------------------------------------------------------------------
        # Flow
        # ------------------------------------------------------------------

        builder.add_edge(
            START,
            "load_memory",
            
        )

        builder.add_edge(
             "load_memory",
            "query_rewrite",
        )

        builder.add_edge(
                     "query_rewrite",
                    "query_processing",
                )

        builder.add_edge(
            "query_processing",
            "hybrid_search",
        )

        builder.add_edge(
            "hybrid_search",
            "reranking",
        )

        builder.add_edge(
            "reranking",
            "context_builder",
        )

        builder.add_edge(
            "context_builder",
            "prompt_builder",
        )

        
        builder.add_edge(
            "prompt_builder",
            "llm",
        )

        builder.add_edge(
            "llm",
            "citation",
        )

        builder.add_edge(
            "citation",
            "save_memory",
        )

        builder.add_edge(
             "save_memory",
            END,
        )

        return GraphFactory.compile(builder)