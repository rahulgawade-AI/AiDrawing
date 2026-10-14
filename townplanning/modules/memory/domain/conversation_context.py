from dataclasses import dataclass, field

from townplanning.modules.memory.domain.message import Message
from townplanning.modules.memory.domain.rewritten_query import RewrittenQuery

@dataclass(slots=True)
class ConversationContext:

    conversation_id: str | None = None

    messages: list[Message] = field(default_factory=list)

    rewritten_query: RewrittenQuery | None = None