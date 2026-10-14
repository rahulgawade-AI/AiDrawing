from __future__ import annotations

import cv2
import numpy as np


def copy_image(
    image: np.ndarray,
) -> np.ndarray:

    return image.copy()


def is_grayscale(
    image: np.ndarray,
) -> bool:

    return len(image.shape) == 2


def image_size(
    image: np.ndarray,
) -> tuple[int, int]:

    h, w = image.shape[:2]

    return w, h


def to_rgb(
    image: np.ndarray,
) -> np.ndarray:

    return cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB,
    )