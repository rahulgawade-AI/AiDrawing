"""
OCR Page Domain Model.
"""

from dataclasses import dataclass, field

from townplanning.modules.regulations.ocr.domain.ocr_block import OCRBlock


@dataclass(slots=True)
class OCRPage:
    """
    Represents a single OCR processed page.
    """

    page_number: int

    blocks: list[OCRBlock] = field(default_factory=list)

    metadata: dict = field(default_factory=dict)