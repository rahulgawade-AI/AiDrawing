from __future__ import annotations

from townplanning.modules.llm.domain.llm_answer import LLMAnswer

from townplanning.workflows.common.exceptions import (
    WorkflowExecutionError,
)
from townplanning.workflows.common.workflow import Workflow
from townplanning.workflows.question_answering.graph import (
    QuestionAnsweringGraph,
)
from townplanning.workflows.question_answering.nodes import (
    QuestionAnsweringNodes,
)
from townplanning.workflows.question_answering.state import (
    QuestionAnsweringState,
)


class QuestionAnsweringWorkflow(Workflow):
    """
    Question Answering workflow backed by LangGraph.
    """

    def __init__(
        self,
        nodes: QuestionAnsweringNodes,
    ):
        graph_builder = QuestionAnsweringGraph(nodes)
        self._graph = graph_builder.build()

    def run(
        self,
        question: str,
        conversation_id: str | None = None,
    ) -> tuple[LLMAnswer, str | None]:
        """
        Execute the Question Answering workflow.

        Args:
            question: User question.
            conversation_id: Existing conversation id (optional).

        Returns:
            tuple[LLMAnswer, conversation_id]
        """

        state = QuestionAnsweringState(
            question=question,
        )

        state.conversation.conversation_id = conversation_id

        result = self._graph.invoke(state)

        if isinstance(result, dict):
            final_state = QuestionAnsweringState(**result)
        else:
            final_state = result

        if final_state.error:
            raise WorkflowExecutionError(
                final_state.error
            )

        if final_state.answer is None:
            raise WorkflowExecutionError(
                "Workflow completed without producing an answer."
            )

        return (
            final_state.answer,
            final_state.conversation.conversation_id,
        )