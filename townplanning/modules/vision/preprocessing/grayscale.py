from __future__ import annotations

import cv2
import numpy as np


class GrayScale:
    """
    Converts image to grayscale.
    """

    def process(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        if len(image.shape) == 2:
            return image.copy()

        return cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )