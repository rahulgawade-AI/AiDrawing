from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import Polygon as ShapelyPolygon

from .point import Point


@dataclass(slots=True)
class Polygon:

    vertices: list[Point]

    @property
    def shapely(self) -> ShapelyPolygon:
        return ShapelyPolygon(
            [
                p.to_tuple()
                for p in self.vertices
            ]
        )

    @property
    def area(self) -> float:
        return self.shapely.area

    @property
    def perimeter(self) -> float:
        return self.shapely.length

    @property
    def centroid(self) -> Point:

        c = self.shapely.centroid

        return Point(
            c.x,
            c.y,
        )

    def buffer(
        self,
        distance: float,
    ) -> "Polygon":

        poly = self.shapely.buffer(distance)

        return Polygon(
            vertices=[
                Point(x, y)
                for x, y in poly.exterior.coords[:-1]
            ]
        )