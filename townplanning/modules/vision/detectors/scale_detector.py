from __future__ import annotations

import re

from townplanning.modules.vision.detectors.base_detector import BaseDetector
from townplanning.modules.vision.domain.drawing import Drawing


class ScaleDetector(BaseDetector):

    SCALE_REGEX = re.compile(
        r"1\s*:\s*(\d+)"
    )

    def detect(
        self,
        drawing: Drawing,
    ) -> float | None:

        for page in drawing.pages:

            for block in page.texts:

                match = self.SCALE_REGEX.search(
                    block.text
                )

                if match:
                    return float(match.group(1))

        return None