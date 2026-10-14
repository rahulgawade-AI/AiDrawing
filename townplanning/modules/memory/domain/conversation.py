from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Conversation:

    id: str

    created_at: datetime

    updated_at: datetime