"""
OCR Block Domain Model.

Represents a single text block extracted from a PDF page by an OCR engine.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class OCRBlock:
    """
    A single OCR text block.
    """

    #
    # Unique block identifier.
    #
    id: str

    #
    # PDF page number.
    #
    page: int

    #
    # Extracted text.
    #
    text: str

    #
    # OCR confidence (0.0 - 1.0).
    #
    confidence: float

    #
    # Language detected by OCR.
    #
    language: str = ""

    #
    # Bounding polygon in PDF/image coordinates.
    #
    # Example:
    # [
    #     [x1, y1],
    #     [x2, y2],
    #     [x3, y3],
    #     [x4, y4],
    # ]
    #
    polygon: list[list[float]] = field(default_factory=list)

    #
    # Additional OCR metadata.
    #
    metadata: dict = field(default_factory=dict)