from __future__ import annotations

import cv2
import numpy as np


class Denoise:

    def process(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        return cv2.fastNlMeansDenoising(
            image,
            None,
            10,
            7,
            21,
        )