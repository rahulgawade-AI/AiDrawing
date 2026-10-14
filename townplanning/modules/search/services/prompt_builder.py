from __future__ import annotations

from townplanning.modules.llm.domain.prompt import Prompt
from townplanning.modules.search.dom.context import Context
from townplanning.modules.query.dom.query import Query

class PromptBuilder:
    """
    Builds prompts for the LLM.
    """

    def build(
        self,
        *,
        question: str,
        context: Context,
    ) -> Prompt:

        system_prompt = self._build_system_prompt()

        user_prompt = self._build_user_prompt(
            question=question,
            context=context,
        )

        return Prompt(
            system=system_prompt,
            user=user_prompt,
        )

    ####################################################################
    # Private
    ####################################################################

    def _build_system_prompt(self) -> str:

        return """
You are an expert Urban Development Control Regulations (UDCPR) assistant.

Your responsibilities:

- Answer ONLY using the supplied context.
- Never invent regulations.
- Never use outside knowledge.
- If the answer is not contained in the supplied context,
  clearly state that the information is unavailable.
- Use clear professional language.
- If multiple regulations are relevant,
  combine them into one coherent answer.
"""

    def _build_user_prompt(
        self,
        *,
        question: str,
        context: Context,
    ) -> str:

        return f"""
QUESTION

{question}

============================================================

CONTEXT

{context.text}

============================================================

Instructions

Answer ONLY from the supplied context.

If the context does not contain enough information,
say so clearly.

Do not use outside knowledge.
"""