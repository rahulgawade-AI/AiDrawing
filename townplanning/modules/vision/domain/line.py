from __future__ import annotations

from dataclasses import dataclass

from .point import Point


@dataclass(slots=True, frozen=True)
class Line:
    """
    Represents a line segment.
    """

    start: Point
    end: Point

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def midpoint(self) -> Point:
        return Point(
            x=(self.start.x + self.end.x) / 2,
            y=(self.start.y + self.end.y) / 2,
        )