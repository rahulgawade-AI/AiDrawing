from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(slots=True)
class OCRRecord:
    id: UUID = field(default_factory=uuid4)

    source: str = ""

    page_number: int = 0

    original_text: str = ""

    translated_text: str | None = None

    metadata: dict = field(default_factory=dict)