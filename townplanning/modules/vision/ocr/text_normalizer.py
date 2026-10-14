from __future__ import annotations

import re


class TextNormalizer:
    """
    Cleans OCR output before downstream processing.
    """

    _MULTIPLE_SPACES = re.compile(r"\s+")

    def normalize(
        self,
        text: str,
    ) -> str:

        text = text.replace("\n", " ")
        text = text.replace("\t", " ")

        text = self._MULTIPLE_SPACES.sub(" ", text)

        return text.strip()