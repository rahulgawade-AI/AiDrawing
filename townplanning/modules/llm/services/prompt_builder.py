from __future__ import annotations

from townplanning.modules.llm.domain.prompt import Prompt
from townplanning.modules.query.dom.query import Query
from townplanning.modules.search.dom.context import Context
from townplanning.modules.memory.domain.message import Message


class PromptBuilder:
    """
    Builds prompts for LLM interactions.
    """

    SYSTEM_PROMPT = """
You are an expert assistant for the Unified Development Control and Promotion Regulations (UDCPR).

Instructions:

- Answer ONLY using the supplied context.
- Never invent regulations, clauses, values, tables, or procedures.
- Never use outside knowledge.
- If the answer is not present in the supplied context, clearly state that the information is unavailable.
- Quote regulation numbers, clause numbers, and chapter numbers whenever available.
- Prefer exact wording from the regulations whenever possible.
- If multiple context sections are relevant, combine them into a single coherent answer.
- Keep answers concise, professional and factually accurate.
- Do NOT mention the expanded query, detected intent or extracted entities.
"""

    ####################################################################
    # Public
    ####################################################################

    def build(
        self,
        *,
        query: Query,
        context: Context,
        history: list[Message] | None = None,
    ) -> Prompt:

        user_prompt = self._build_user_prompt(
            query=query,
            context=context,
            history=history,
        )

        return Prompt(
            system=self.SYSTEM_PROMPT.strip(),
            user=user_prompt.strip(),
        )

    ####################################################################
    # Private
    ####################################################################

    def _build_user_prompt(
        self,
        *,
        query: Query,
        context: Context,
        history: list[Message] | None,
    ) -> str:

        entity_text = "\n".join(
            f"- {entity.entity_type}: {entity.value}"
            for entity in query.entities
        )

        if not entity_text:
            entity_text = "None"

        conversation = self._build_conversation(history)

        return f"""
QUESTION

{query.original}

============================================================

PREVIOUS CONVERSATION

{conversation}

============================================================

DETECTED INTENT

{query.intent.name}

============================================================

EXTRACTED ENTITIES

{entity_text}

============================================================

EXPANDED QUERY

{query.expanded}

============================================================

CONTEXT

{context.text}

============================================================

Instructions

1. Answer ONLY using the supplied context.
2. Use the previous conversation only for understanding the user's intent.
3. Never use the conversation as factual evidence.
4. Do NOT use outside knowledge.
5. If the context does not contain enough information, clearly state that the answer is unavailable.
6. When regulation numbers or clause numbers are present, include them naturally.
7. Do NOT mention the detected intent, expanded query, extracted entities or previous conversation.
"""

    def _build_conversation(
        self,
        history: list[Message] | None,
    ) -> str:

        if not history:
            return "None"

        messages = []

        # Last 6 messages (3 user/assistant turns)
        for message in history[-6:]:

            role = message.role.capitalize()

            messages.append(
                f"{role}: {message.message}"
            )

        return "\n".join(messages)