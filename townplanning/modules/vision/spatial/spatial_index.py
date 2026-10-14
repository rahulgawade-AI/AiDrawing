from __future__ import annotations

from math import hypot

from shapely.geometry import Point
from shapely.geometry import Polygon


class SpatialIndex:

    """
    Shared spatial helper functions.
    """

    @staticmethod
    def distance(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> float:

        return hypot(
            x2 - x1,
            y2 - y1,
        )

    @staticmethod
    def inside_polygon(
        x: float,
        y: float,
        polygon: Polygon,
    ) -> bool:

        return polygon.contains(
            Point(x, y)
        )