"""
Business entity representing one regulation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from datetime import UTC

@dataclass(slots=True)
class Regulation:

    id: str

    number: str

    chapter: str

    title: str

    text: str

    page_start: int

    page_end: int

    source_document: str = "UDCPR"

    version: str = "2020"

    metadata: dict = field(default_factory=dict)

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )