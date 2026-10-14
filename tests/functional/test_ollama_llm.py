from townplanning.modules.llm.domain.prompt import Prompt
from townplanning.modules.llm.providers.ollama_provider import OllamaProvider
from townplanning.modules.llm.services.llm_service import LLMService


def main():

    provider = OllamaProvider()
    llm = LLMService(provider)

    while True:

        question = input("\nQuestion (type 'exit' to quit): ").strip()

        if question.lower() == "exit":
            break

        prompt = Prompt(
            system="""
You are an expert Urban Development Control and Promotion Regulations (UDCPR) assistant.

Answer only from the supplied context.
""",
            user=question,
        )

        answer = llm.generate(
            question=question,
            prompt=prompt,
        )

        print("\n" + "=" * 80)
        print(answer.answer)
        print("=" * 80)


if __name__ == "__main__":
    main()