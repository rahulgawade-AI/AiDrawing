from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class ImageLoader:
    """
    Loads engineering drawings from disk.

    Supported formats:
        - PNG
        - JPG / JPEG
        - TIFF
        - BMP

    PDF support will be added later.
    """

    SUPPORTED_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tif",
        ".tiff",
    }

    def load(
        self,
        image_path: str | Path,
    ) -> np.ndarray:

        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(image_path)

        if image_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported image format: {image_path.suffix}"
            )

        image = cv2.imread(
            str(image_path),
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise RuntimeError(
                f"Unable to read image: {image_path}"
            )

        return image