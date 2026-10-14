from __future__ import annotations

import re

from townplanning.modules.vision.domain.plot_number import (
    PlotNumber,
)


class PlotNumberExtractor:
    """
    Extracts plot / survey numbers from OCR text.

    Supported examples:

        S.NO. 78/5
        S.NO 78/5
        SURVEY NO. 78/5
        SURVEY NUMBER 78/5
        PLOT NO. 78/5
        PLOT NUMBER 78/5
        PLOT 78/5
    """

    _PATTERN = re.compile(
        r"""
        (?:
            \bS\.?\s*NO\.?
            |
            \bSURVEY\s*(?:NO\.?|NUMBER)?
            |
            \bPLOT\s*(?:NO\.?|NUMBER)?
        )
        \s*
        [:.\-]?
        \s*
        (
            [A-Z0-9]+
            (?:
                \s*/\s*[A-Z0-9]+
            )*
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def extract(
        self,
        text: str,
        confidence: float = 1.0,
    ) -> PlotNumber | None:

        if not text:
            return None

        match = self._PATTERN.search(text)

        if not match:
            return None

        value = re.sub(
            r"\s+",
            "",
            match.group(1),
        ).upper()

        return PlotNumber(
            value=value,
            source_text=text,
            confidence=confidence,
        )
