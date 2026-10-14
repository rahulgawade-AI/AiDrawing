from __future__ import annotations

import re

from townplanning.modules.vision.domain.scale import Scale


class ScaleExtractor:

    _PATTERN = re.compile(
        r"""
        \bscale\b
        \s*
        1
        \s*
        :
        \s*
        (\d+(?:\.\d+)?)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def extract(
        self,
        text: str,
    ) -> Scale | None:

        match = self._PATTERN.search(text)

        if match is None:
            return None

        denominator_text = match.group(1)

        denominator = int(
            float(denominator_text)
        )

        return Scale(
            numerator=1,
            denominator=denominator,
            source_text=text,
        )