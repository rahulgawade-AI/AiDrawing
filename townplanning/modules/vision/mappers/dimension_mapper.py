from __future__ import annotations

from townplanning.modules.vision.domain.dimension import (
    Dimension,
)
from townplanning.modules.vision.domain.text_block import (
    TextBlock,
)

from townplanning.modules.vision.ocr.dimension_extractor import (
    DimensionExtractor,
)


class DimensionMapper:
    """
    Maps OCR text blocks into spatially-aware dimensions.

    The OCR bounding box is passed to DimensionExtractor so
    every Dimension retains its position in the source drawing.
    """

    def __init__(self):

        self.extractor = DimensionExtractor()

    def map(
        self,
        blocks: list[TextBlock],
    ) -> list[Dimension]:

        dimensions: list[Dimension] = []

        for block in blocks:

            extracted = self.extractor.extract(
                text=block.text,
                bounding_box=block.bounding_box,
                confidence=block.confidence,
            )

            dimensions.extend(
                extracted
            )

        return dimensions