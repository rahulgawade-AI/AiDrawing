from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Message:

    id: str

    conversation_id: str

    role: str

    message: str

    created_at: datetime

    token_count: int = 0