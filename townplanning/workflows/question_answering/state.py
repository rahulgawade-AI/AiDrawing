from __future__ import annotations

from dataclasses import dataclass, field

from townplanning.modules.citations.domain.citation import Citation
from townplanning.modules.llm.domain.llm_answer import LLMAnswer
from townplanning.modules.llm.domain.prompt import Prompt
from townplanning.modules.query.dom.query import Query
from townplanning.modules.search.dom.context import Context
from townplanning.modules.search.dom.search_result import SearchResult
from townplanning.modules.memory.domain.conversation_context import (
    ConversationContext,
)



@dataclass(slots=True)
class QuestionAnsweringState:

    question: str

    query: Query | None = None

    search_results: list[SearchResult] = field(default_factory=list)

    context: Context | None = None

    prompt: Prompt | None = None

    answer: LLMAnswer | None = None

    citations: list[Citation] = field(default_factory=list)

    error: str | None = None

    #conversation_id: str | None = None

    #history: list[Message] = field(default_factory=list)

    #rewritten_question: str = ""
    
    conversation: ConversationContext = field(
        default_factory=ConversationContext
    )