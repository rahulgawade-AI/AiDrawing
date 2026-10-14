from __future__ import annotations

from shapely.geometry import Point


class TextAssociation:
    """
    Determines which texts belong inside or outside
    the domain plot polygon.
    """

    def associate(
        self,
        texts,
        polygon,
    ):

        inside = []

        outside = []

        #
        # Domain Polygon
        #
        vertices = polygon.vertices

        if not vertices:

            return inside, outside

        #
        # Build Shapely polygon from the domain
        # polygon vertices only for the geometric
        # containment calculation.
        #
        coordinates = [
            (
                vertex.x,
                vertex.y,
            )
            for vertex in vertices
        ]

        from shapely.geometry import Polygon as ShapelyPolygon

        geometry = ShapelyPolygon(
            coordinates
        )

        for block in texts:

            center = block.bounding_box.center

            point = Point(
                center.x,
                center.y,
            )

            if geometry.contains(point):

                inside.append(block)

            else:

                outside.append(block)

        return inside, outside