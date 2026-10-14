from __future__ import annotations

from pathlib import Path

import numpy as np

from townplanning.modules.vision.domain.bounding_box import (
    BoundingBox,
)
from townplanning.modules.vision.domain.dimension import (
    Dimension,
)
from townplanning.modules.vision.domain.plot_area import (
    PlotArea,
)
from townplanning.modules.vision.domain.plot_number import (
    PlotNumber,
)
from townplanning.modules.vision.domain.scale import (
    Scale,
)
from townplanning.modules.vision.domain.text_block import (
    TextBlock,
)

from townplanning.modules.vision.ocr.area_extractor import (
    AreaExtractor,
)
from townplanning.modules.vision.ocr.dimension_extractor import (
    DimensionExtractor,
)
from townplanning.modules.vision.ocr.ocr_engine import (
    OCREngine,
)
from townplanning.modules.vision.ocr.paddle_ocr_engine import (
    PaddleOCREngine,
)
from townplanning.modules.vision.ocr.plot_number_extractor import (
    PlotNumberExtractor,
)
from townplanning.modules.vision.ocr.scale_extractor import (
    ScaleExtractor,
)
from townplanning.modules.vision.ocr.text_normalizer import (
    TextNormalizer,
)


class OCRService:
    """
    Application service for OCR processing.

    Extracts:

        - OCR text blocks
        - spatial dimensions
        - drawing scale
        - plot area
        - plot number

    OCR coordinates are converted back to the
    original image coordinate system before
    dimensions are created.
    """

    def __init__(
        self,
        engine: OCREngine | None = None,
    ):

        self._engine = (
            engine
            or PaddleOCREngine()
        )

        self._normalizer = (
            TextNormalizer()
        )

        self._dimension_extractor = (
            DimensionExtractor()
        )

        self._scale_extractor = (
            ScaleExtractor()
        )

        self._area_extractor = (
            AreaExtractor()
        )

        self._plot_number_extractor = (
            PlotNumberExtractor()
        )

    def process(
        self,
        image: str | Path | np.ndarray,
        page: int = 1,
        coordinate_scale_x: float = 1.0,
        coordinate_scale_y: float = 1.0,
    ) -> tuple[
        list[TextBlock],
        list[Dimension],
        Scale | None,
        PlotArea | None,
        PlotNumber | None,
    ]:

        #
        # OCR
        #
        text_blocks = self._engine.extract(
            image,
            page=page,
        )

        #
        # Extracted dimensions
        #
        dimensions: list[Dimension] = []

        #
        # Drawing scale
        #
        scale: Scale | None = None

        #
        # Plot area
        #
        area: PlotArea | None = None

        #
        # Plot number
        #
        plot_number: PlotNumber | None = None

        for block in text_blocks:

            #
            # --------------------------------------------------
            # Convert OCR coordinates back to original image
            # coordinates.
            # --------------------------------------------------
            #
            box = block.bounding_box

            block.bounding_box = BoundingBox(
                min_x=(
                    box.min_x
                    * coordinate_scale_x
                ),
                min_y=(
                    box.min_y
                    * coordinate_scale_y
                ),
                max_x=(
                    box.max_x
                    * coordinate_scale_x
                ),
                max_y=(
                    box.max_y
                    * coordinate_scale_y
                ),
            )

            #
            # Normalize OCR text.
            #
            block.text = (
                self._normalizer.normalize(
                    block.text
                )
            )

            #
            # --------------------------------------------------
            # Dimensions
            # --------------------------------------------------
            #
            dimensions.extend(
                self._dimension_extractor.extract(
                    text=block.text,
                    bounding_box=block.bounding_box,
                    confidence=block.confidence,
                )
            )

            #
            # --------------------------------------------------
            # Scale
            # --------------------------------------------------
            #
            detected_scale = (
                self._scale_extractor.extract(
                    block.text
                )
            )

            if (
                detected_scale is not None
                and scale is None
            ):
                scale = detected_scale

            #
            # --------------------------------------------------
            # Plot area
            # --------------------------------------------------
            #
            detected_area = (
                self._area_extractor.extract(
                    text=block.text,
                    confidence=block.confidence,
                )
            )

            if (
                detected_area is not None
                and area is None
            ):
                area = detected_area

            #
            # --------------------------------------------------
            # Plot number
            # --------------------------------------------------
            #
            detected_plot_number = (
                self._plot_number_extractor.extract(
                    block.text,
                    confidence=block.confidence,
                )
            )

            if (
                detected_plot_number is not None
                and plot_number is None
            ):
                plot_number = (
                    detected_plot_number
                )

        return (
            text_blocks,
            dimensions,
            scale,
            area,
            plot_number,
        )