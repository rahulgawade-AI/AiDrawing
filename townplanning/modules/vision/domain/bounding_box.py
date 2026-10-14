from __future__ import annotations

from dataclasses import dataclass

from .point import Point


@dataclass(slots=True, frozen=True)
class BoundingBox:

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def center(self) -> Point:
        return Point(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
        )

    def contains(
        self,
        point: Point,
    ) -> bool:

        return (
            self.min_x <= point.x <= self.max_x
            and
            self.min_y <= point.y <= self.max_y
        )