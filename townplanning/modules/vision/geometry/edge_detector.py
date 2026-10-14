from __future__ import annotations

import cv2
import numpy as np


class EdgeDetector:

    def detect(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        return cv2.Canny(
            image,
            50,
            150,
        )