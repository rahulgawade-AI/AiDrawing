from __future__ import annotations

import cv2
import numpy as np


class Resize:
    """
    Upscale image before OCR.
    """

    def process(
        self,
        image: np.ndarray,
        scale: float = 2.0,
    ) -> np.ndarray:

        return cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )