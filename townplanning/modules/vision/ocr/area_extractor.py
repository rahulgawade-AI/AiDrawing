from __future__ import annotations

import re

from townplanning.modules.vision.domain.plot_area import (
    PlotArea,
)


class AreaExtractor:
    """
    Extracts explicitly labelled plot areas from OCR text.
    """

    _PATTERN = re.compile(
        r"""
        (?:
            plot
            \s*
            area
            \s*
        )?
        (
            \d+(?:\.\d+)?
        )
        \s*
        (
            sq\.?\s*m\.?
            |
            sqm
            |
            m2
            |
            m²
            |
            sq\.?\s*ft\.?
            |
            sqft
            |
            ft2
            |
            ft²
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def extract(
        self,
        text: str,
        confidence: float = 1.0,
    ) -> PlotArea | None:

        #
        # Only accept an area when the OCR text
        # actually contains an area unit.
        #
        match = self._PATTERN.search(text)

        if match is None:
            return None

        value = float(
            match.group(1)
        )

        unit = (
            match.group(2)
            .strip()
            .lower()
        )

        return PlotArea(
            value=value,
            unit=unit,
            source_text=text,
            confidence=confidence,
        )
