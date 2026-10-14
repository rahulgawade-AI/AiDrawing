from __future__ import annotations

from dataclasses import dataclass

from .bounding_box import BoundingBox


@dataclass(slots=True)
class TextBlock:

    text: str

    bounding_box: BoundingBox

    confidence: float

    page: int