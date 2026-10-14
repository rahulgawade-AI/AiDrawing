from __future__ import annotations

from dataclasses import dataclass

from .point import Point


@dataclass(slots=True)
class Rectangle:
    """
    Axis-aligned rectangle.

    Used for:
        - OCR bounding boxes
        - Object detection
        - Image regions
        - Room bounding boxes
    """

    left: float

    top: float

    right: float

    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Point:
        return Point(
            x=(self.left + self.right) / 2,
            y=(self.top + self.bottom) / 2,
        )

    def contains(
        self,
        point: Point,
    ) -> bool:
        return (
            self.left <= point.x <= self.right
            and self.top <= point.y <= self.bottom
        )

    def intersects(
        self,
        other: "Rectangle",
    ) -> bool:
        return not (
            self.right < other.left
            or self.left > other.right
            or self.bottom < other.top
            or self.top > other.bottom
        )

    def expand(
        self,
        margin: float,
    ) -> "Rectangle":
        return Rectangle(
            left=self.left - margin,
            top=self.top - margin,
            right=self.right + margin,
            bottom=self.bottom + margin,
        )

    def to_tuple(
        self,
    ) -> tuple[float, float, float, float]:
        return (
            self.left,
            self.top,
            self.right,
            self.bottom,
        )