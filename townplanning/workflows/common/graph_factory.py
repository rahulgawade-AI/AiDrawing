from __future__ import annotations

from langgraph.graph import StateGraph


class GraphFactory:
    """
    Factory responsible for compiling LangGraph workflows.
    """

    @staticmethod
    def compile(builder: StateGraph):
        return builder.compile()