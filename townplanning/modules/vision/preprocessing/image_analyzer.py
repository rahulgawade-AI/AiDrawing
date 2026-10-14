from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(slots=True)
class ImageAnalysis:

    width: int

    height: int

    grayscale: bool

    low_contrast: bool

    noisy: bool

    blurred: bool

    needs_resize: bool

    needs_clahe: bool

    needs_deskew: bool


class ImageAnalyzer:

    """
    Analyse engineering drawings before OCR.
    """

    def analyze(
        self,
        image: np.ndarray,
    ) -> ImageAnalysis:

        h, w = image.shape[:2]

        grayscale = len(image.shape) == 2

        gray = image

        if not grayscale:

            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY,
            )

        contrast = gray.std()

        low_contrast = contrast < 40

        lap = cv2.Laplacian(
            gray,
            cv2.CV_64F,
        ).var()

        blurred = lap < 120

        noisy = gray.std() > 70

        needs_resize = min(h, w) < 1200

        needs_clahe = low_contrast

        needs_deskew = True

        return ImageAnalysis(

            width=w,

            height=h,

            grayscale=grayscale,

            low_contrast=low_contrast,

            noisy=noisy,

            blurred=blurred,

            needs_resize=needs_resize,

            needs_clahe=needs_clahe,

            needs_deskew=needs_deskew,

        )