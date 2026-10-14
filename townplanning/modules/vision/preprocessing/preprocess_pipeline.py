from __future__ import annotations

import numpy as np

from .image_enhancer import ImageEnhancer
from .grayscale import GrayScale
from .resize import Resize
from .clahe import CLAHE
from .denoise import Denoise
from .threshold import Threshold
from .morphology import Morphology
from .sharpen import Sharpen
from .image_analyzer import ImageAnalyzer
from .deskew import Deskew

class PreprocessPipeline:

    def __init__(self):

        self.enhancer = ImageEnhancer()

        self.gray = GrayScale()

        self.resize = Resize()

        self.clahe = CLAHE()

        self.denoise = Denoise()

        self.threshold = Threshold()

        self.morphology = Morphology()

        self.sharpen = Sharpen()
        self.analyzer = ImageAnalyzer()

        self.deskew = Deskew()

    def process(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        image = self.enhancer.process(image)

        image = self.gray.process(image)

        analysis = self.analyzer.analyze(
         image,
        )

        if analysis.needs_resize:

            image = self.resize.process(image)

        if analysis.needs_clahe:

            image = self.clahe.process(image)

        if analysis.noisy:

            image = self.denoise.process(image)

        if analysis.needs_deskew:

            image = self.deskew.process(image)

        image = self.threshold.adaptive(image)

        image = self.morphology.closing(image)

        image = self.sharpen.process(image)

        return image