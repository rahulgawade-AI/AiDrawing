from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(slots=True, frozen=True)
class Point:
    """
    Represents a point in 2D space.

    Coordinates are stored in meters once calibrated.
    Before calibration they may represent image pixels.
    """

    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        """
        Calculate Euclidean distance.
        """
        return sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2
        )

    def translate(
        self,
        dx: float,
        dy: float,
    ) -> "Point":
        return Point(
            x=self.x + dx,
            y=self.y + dy,
        )

    def scale(
        self,
        factor: float,
    ) -> "Point":
        return Point(
            x=self.x * factor,
            y=self.y * factor,
        )

    def to_tuple(self) -> tuple[float, float]:
        return (
            self.x,
            self.y,
        )