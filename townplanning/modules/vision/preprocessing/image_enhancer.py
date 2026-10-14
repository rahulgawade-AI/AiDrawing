from __future__ import annotations

import cv2
import numpy as np


class ImageEnhancer:
    """
    Basic enhancement for engineering drawings.
    """

    def process(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        alpha = 1.25
        beta = 8

        enhanced = cv2.convertScaleAbs(
            image,
            alpha=alpha,
            beta=beta,
        )

        return enhanced