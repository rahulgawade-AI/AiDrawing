from __future__ import annotations

import cv2
import numpy as np


class Morphology:

    def closing(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        kernel = np.ones((3, 3), np.uint8)

        return cv2.morphologyEx(
            image,
            cv2.MORPH_CLOSE,
            kernel,
        )

    def opening(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        kernel = np.ones((3, 3), np.uint8)

        return cv2.morphologyEx(
            image,
            cv2.MORPH_OPEN,
            kernel,
        )