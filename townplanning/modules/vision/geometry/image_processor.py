from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class ImageProcessor:
    """
    Performs preprocessing before geometry detection.
    """

    def load(
        self,
        image: str | Path | np.ndarray,
    ) -> np.ndarray:

        #
        # Image is already loaded.
        #
        if isinstance(image, np.ndarray):

            if image.size == 0:
                raise ValueError(
                    "Received an empty image."
                )

            return image

        #
        # Image is a file path.
        #
        image_path = Path(image)

        loaded = cv2.imread(
            str(image_path)
        )

        if loaded is None:
            raise FileNotFoundError(
                image_path
            )

        return loaded

    def grayscale(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        if len(image.shape) == 2:
            return image

        return cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

    def denoise(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        return cv2.GaussianBlur(
            image,
            (5, 5),
            0,
        )

    def threshold(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        return cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            15,
            5,
        )