from townplanning.core.container import ApplicationContainer
from townplanning.workflows.question_answering.nodes import (
    QuestionAnsweringNodes,
)
from townplanning.workflows.question_answering.workflow import (
    QuestionAnsweringWorkflow,
)
from townplanning.modules.memory.services.query_rewrite_service import (
    QueryRewriteService,
)

def build_workflow():

    container = ApplicationContainer()

    nodes = QuestionAnsweringNodes(
        query_processing_service=container.query_processing_service(),
        hybrid_search_service=container.hybrid_search_service(),
        reranking_service=container.reranking_service(),
        context_builder_service=container.context_builder(),
        prompt_builder=container.prompt_builder(),
        llm_service=container.llm_service(),
        citation_service=container.citation_service(),
        memory_service=container.memory_service(),
        query_rewrite_service=QueryRewriteService(), 
    )

    return QuestionAnsweringWorkflow(nodes)


def main():

    workflow = build_workflow()
    conversation_id = None

    while True:

        print("\n" + "=" * 100)

        question = input("Ask UDCPR (type 'exit' to quit): ").strip()

        if question.lower() in ("exit", "quit"):
            break

        try:

            answer,conversation_id = workflow.run(question,conversation_id)
            print("\nConversation ID:", conversation_id)

            print("\n" + "=" * 100)
            print("ANSWER")
            print("=" * 100)

            print(answer.answer)

            print("\n" + "=" * 100)
            print("MODEL")
            print("=" * 100)

            print(answer.model)

            print("\nExecution Time:", round(answer.execution_time, 2), "seconds")

        except Exception as ex:

            print("\nERROR")
            print(ex)


if __name__ == "__main__":
    main()