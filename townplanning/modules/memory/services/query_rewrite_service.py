from __future__ import annotations

import re

from townplanning.modules.memory.domain.rewritten_query import (
    RewrittenQuery,
)
from townplanning.modules.memory.domain.message import Message


class QueryRewriteService:
    """
    Rewrites conversational follow-up questions into
    standalone search queries.
    """

    FOLLOWUP_PATTERNS = [

        r"^what about",
        r"^how about",
        r"^and",
        r"^also",
        r"^same",
        r"^it",
        r"^they",
        r"^those",
        r"^these",
        r"^this",
        r"^that",
        r"^its",
        r"^their",
        r"^can we",
        r"^can i",
        r"^is it",
        r"^does it",

    ]

    def __init__(
        self,
        history_window: int = 6,
    ):

        self.history_window = history_window

    ####################################################################
    # Public
    ####################################################################

    def rewrite(
        self,
        question: str,
        history: list[Message],
    ) -> RewrittenQuery:

        question = question.strip()

        if not history:

            return RewrittenQuery(
                original=question,
                rewritten=question,
                was_rewritten=False,
            )

        if not self._is_followup(question):

            return RewrittenQuery(
                original=question,
                rewritten=question,
                was_rewritten=False,
            )

        previous = self._find_previous_user_question(history)

        if previous is None:

            return RewrittenQuery(
                original=question,
                rewritten=question,
                was_rewritten=False,
            )

        rewritten = (
            f"{previous}\n\n"
            f"Follow-up question:\n"
            f"{question}"
        )

        return RewrittenQuery(
            original=question,
            rewritten=rewritten,
            was_rewritten=True,
        )

    ####################################################################
    # Helpers
    ####################################################################

    def _is_followup(
        self,
        question: str,
    ) -> bool:

        question = question.lower()

        return any(
            re.match(pattern, question)
            for pattern in self.FOLLOWUP_PATTERNS
        )

    def _find_previous_user_question(
        self,
        history: list[Message],
    ) -> str | None:

        user_messages = [
            m.message
            for m in history[-self.history_window:]
            if m.role == "user"
        ]

        if not user_messages:
            return None

        return user_messages[-1]