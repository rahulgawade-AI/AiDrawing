from dataclasses import dataclass, field

from townplanning.modules.citations.domain.citation import Citation


@dataclass(slots=True)
class LLMAnswer:

    question: str

    answer: str

    model: str

    prompt_tokens: int

    completion_tokens: int

    finish_reason: str

    execution_time: float

    citations: list[Citation] = field(default_factory=list)