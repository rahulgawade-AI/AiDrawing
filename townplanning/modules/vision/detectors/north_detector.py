from __future__ import annotations

from townplanning.modules.vision.detectors.base_detector import (
    BaseDetector,
)
from townplanning.modules.vision.domain.drawing import Drawing
from townplanning.modules.vision.domain.north_arrow import (
    NorthArrow,
)


class NorthDetector(BaseDetector):
    """
    Detects the north arrow from OCR text.

    Current strategy:
        - "N" is treated as a north indicator.
        - "NORTH" is treated as a north indicator.

    The OCR TextBlock position is retained so that
    the NorthArrow can later be spatially located.
    """

    def detect(
        self,
        drawing: Drawing,
        texts=None,
    ) -> NorthArrow | None:

        #
        # --------------------------------------------------
        # Prefer OCR TextBlocks.
        # --------------------------------------------------
        #

        if texts:

            for block in texts:

                text = (
                    block.text
                    .strip()
                    .upper()
                )

                #
                # Exact N marker.
                #
                if text == "N":

                    return NorthArrow(
                        center=block.bounding_box.center,
                        angle=0.0,
                        confidence=block.confidence,
                        detected_text=block.text,
                        source="ocr",
                    )

                #
                # Explicit NORTH text.
                #
                if text == "NORTH":

                    return NorthArrow(
                        center=block.bounding_box.center,
                        angle=0.0,
                        confidence=block.confidence,
                        detected_text=block.text,
                        source="ocr",
                    )

        #
        # --------------------------------------------------
        # Fallback to Drawing text.
        #
        # Useful when a parser has already populated
        # Page.texts.
        # --------------------------------------------------
        #

        for page in drawing.pages:

            for block in page.texts:

                text = (
                    block.text
                    .strip()
                    .upper()
                )

                if text == "N":

                    return NorthArrow(
                        center=block.bounding_box.center,
                        angle=0.0,
                        confidence=block.confidence,
                        detected_text=block.text,
                        source="drawing",
                    )

                if text == "NORTH":

                    return NorthArrow(
                        center=block.bounding_box.center,
                        angle=0.0,
                        confidence=block.confidence,
                        detected_text=block.text,
                        source="drawing",
                    )

        return None