from __future__ import annotations

import numpy as np

from townplanning.modules.vision.domain.text_block import TextBlock
from townplanning.modules.vision.ocr.ocr_engine import OCREngine

from townplanning.modules.vision.preprocessing.grayscale import GrayScale
from townplanning.modules.vision.preprocessing.clahe import CLAHE
from townplanning.modules.vision.preprocessing.threshold import Threshold
from townplanning.modules.vision.preprocessing.sharpen import Sharpen
from townplanning.modules.vision.preprocessing.resize import Resize


class MultiPassOCR:

    """
    Executes OCR on multiple processed versions
    of the same engineering drawing.
    """

    def __init__(
        self,
        engine: OCREngine,
    ):

        self.engine = engine

        self.gray = GrayScale()

        self.resize = Resize()

        self.clahe = CLAHE()

        self.threshold = Threshold()

        self.sharpen = Sharpen()

    def process(
        self,
        image: np.ndarray,
    ) -> list[list[TextBlock]]:

        results = []

        #
        # Original
        #
        results.append(
            self.engine.extract(image)
        )

        #
        # Grayscale
        #
        gray = self.gray.process(image)

        results.append(
            self.engine.extract(gray)
        )

        #
        # CLAHE
        #
        clahe = self.clahe.process(gray)

        results.append(
            self.engine.extract(clahe)
        )

        #
        # Adaptive Threshold
        #
        binary = self.threshold.adaptive(clahe)

        results.append(
            self.engine.extract(binary)
        )

        #
        # Sharpen
        #
        sharp = self.sharpen.process(binary)

        results.append(
            self.engine.extract(sharp)
        )

        #
        # Upscaled
        #
        upscaled = self.resize.process(image)

        results.append(
            self.engine.extract(upscaled)
        )

        return results