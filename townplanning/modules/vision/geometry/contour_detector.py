from __future__ import annotations

import cv2
import numpy as np


class ContourDetector:

    def detect(
        self,
        image: np.ndarray,
    ):

        contours, _ = cv2.findContours(
            image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        return contours