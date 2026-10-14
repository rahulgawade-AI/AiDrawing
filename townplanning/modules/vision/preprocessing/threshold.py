from __future__ import annotations

import cv2
import numpy as np


class Threshold:

    def adaptive(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        return cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            5,
        )

    def otsu(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        _, out = cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )

        return out