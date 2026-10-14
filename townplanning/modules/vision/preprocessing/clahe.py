from __future__ import annotations

import cv2
import numpy as np


class CLAHE:

    def process(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        if len(image.shape) == 3:

            image = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY,
            )

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8),
        )

        return clahe.apply(image)