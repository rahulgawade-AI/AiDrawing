from __future__ import annotations

import re

from townplanning.modules.vision.domain.dimension import (
    Dimension,
)
from townplanning.modules.vision.domain.line import (
    Line,
)
from townplanning.modules.vision.domain.point import (
    Point,
)
from townplanning.modules.vision.domain.bounding_box import (
    BoundingBox,
)


class DimensionExtractor:
    """
    Extracts physical plot dimensions from OCR text.

    This extractor deliberately ignores numeric values that
    belong to:

        - plot/survey numbers
        - plot areas
        - drawing scales

    Spatial information comes from the OCR BoundingBox.
    """

    _PATTERN = re.compile(
        r"(\d+(?:\.\d+)?)\s*(mm|cm|m|ft|feet|inch|in)?",
        re.IGNORECASE,
    )

    _PLOT_NUMBER_PATTERN = re.compile(
        r"\b(?:s\.?\s*no\.?|survey\s*(?:no\.?)?)\b",
        re.IGNORECASE,
    )

    _AREA_PATTERN = re.compile(
        r"\bplot\s*area\b"
        r"|\b\d+(?:\.\d+)?\s*"
        r"(?:sq\.?\s*m\.?|sqm|m2|m²|"
        r"sq\.?\s*ft\.?|sqft|ft2|ft²)\b",
        re.IGNORECASE,
    )

    _SCALE_PATTERN = re.compile(
        r"\bscale\b"
        r"|\b\d+\s*:\s*\d+\b",
        re.IGNORECASE,
    )

    def extract(
        self,
        text: str,
        bounding_box: BoundingBox | None = None,
        confidence: float = 1.0,
    ) -> list[Dimension]:
        """
        Extract dimensions from one OCR text block.
        """

        normalized = text.strip()

        if not normalized:
            return []

        #
        # Do not interpret survey / plot numbers
        # as dimensions.
        #
        if self._PLOT_NUMBER_PATTERN.search(
            normalized
        ):
            return []

        #
        # Do not interpret plot area as a
        # physical dimension.
        #
        if self._AREA_PATTERN.search(
            normalized
        ):
            return []

        #
        # Do not interpret scale values as
        # physical dimensions.
        #
        if self._SCALE_PATTERN.search(
            normalized
        ):
            return []

        matches = self._PATTERN.findall(
            normalized
        )

        if not matches:
            return []

        dimensions: list[Dimension] = []

        #
        # Build one spatial line for this OCR
        # block.
        #
        line = self._build_line(
            bounding_box
        )

        for value, unit in matches:

            dimensions.append(
                Dimension(
                    line=line,
                    value=float(value),
                    unit=unit or "m",
                    confidence=confidence,
                )
            )

        return dimensions

    def _build_line(
        self,
        bounding_box: BoundingBox | None,
    ) -> Line:
        """
        Convert OCR bounding box into a
        representative dimension line.
        """

        #
        # Fallback for callers without spatial
        # OCR information.
        #
        if bounding_box is None:

            return Line(
                start=Point(
                    x=0,
                    y=0,
                ),
                end=Point(
                    x=0,
                    y=0,
                ),
            )

        center = bounding_box.center

        width = (
            bounding_box.max_x
            - bounding_box.min_x
        )

        height = (
            bounding_box.max_y
            - bounding_box.min_y
        )

        #
        # Horizontal dimension label.
        #
        if width >= height:

            return Line(
                start=Point(
                    x=bounding_box.min_x,
                    y=center.y,
                ),
                end=Point(
                    x=bounding_box.max_x,
                    y=center.y,
                ),
            )

        #
        # Vertical dimension label.
        #
        return Line(
            start=Point(
                x=center.x,
                y=bounding_box.min_y,
            ),
            end=Point(
                x=center.x,
                y=bounding_box.max_y,
            ),
        )