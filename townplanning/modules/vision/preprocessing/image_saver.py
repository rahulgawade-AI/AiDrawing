from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class ImageSaver:
    """
    Saves intermediate preprocessing images.

    Useful for debugging OCR quality.
    """

    def save(
        self,
        image: np.ndarray,
        output_path: str | Path,
    ) -> None:

        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        cv2.imwrite(
            str(output_path),
            image,
        )