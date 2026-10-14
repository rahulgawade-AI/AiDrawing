"""
OCR Block extracted from a PDF page.
"""

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class OCRBlock:
    """
    Represents one OCR text block extracted from a PDF page.
    """

    id: str = field(
        default_factory=lambda: str(uuid4())
    )

    page: int = 0

    text: str = ""

    confidence: float = 0.0

    language: str = ""

    # [x1, y1, x2, y2]
    bbox: list[float] = field(
        default_factory=list
    )

    metadata: dict = field(
        default_factory=dict
    )