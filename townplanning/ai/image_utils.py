"""
Utilities for sending images to AI vision models.
"""

from __future__ import annotations

import base64
from pathlib import Path


def encode_image(
    image_path: str | Path,
) -> str:
    """
    Read an image and return base64-encoded data.

    Ollama accepts base64 image content in the
    message.images field.
    """

    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_file():
        raise ValueError(
            f"Not a file: {path}"
        )

    data = path.read_bytes()

    if not data:
        raise ValueError(
            f"Image is empty: {path}"
        )

    return base64.b64encode(
        data
    ).decode("utf-8")