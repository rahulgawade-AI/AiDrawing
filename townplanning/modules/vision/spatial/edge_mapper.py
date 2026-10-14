from __future__ import annotations

from shapely.geometry import LineString

from townplanning.modules.vision.domain.plot_boundary import (
    PlotBoundary,
)
from townplanning.modules.vision.domain.polygon import (
    Polygon,
)


class EdgeMapper:
    """
    Extracts boundary edges from the domain Polygon.

    Supports:
        - PlotBoundary
        - domain Polygon
    """

    def map(
        self,
        boundary: PlotBoundary | Polygon,
    ) -> list[LineString]:

        #
        # PlotBoundary wrapper
        #
        if isinstance(boundary, PlotBoundary):

            polygon = boundary.polygon

        #
        # Domain Polygon
        #
        elif isinstance(boundary, Polygon):

            polygon = boundary

        else:

            raise TypeError(
                "Expected PlotBoundary or domain Polygon, "
                f"got {type(boundary).__name__}"
            )

        #
        # Domain Polygon stores its geometry
        # as a list of Point objects.
        #
        vertices = polygon.vertices

        if not vertices:

            return []

        #
        # Need at least two vertices
        # to construct an edge.
        #
        if len(vertices) < 2:

            return []

        edges = []

        #
        # Connect every vertex to the next.
        #
        # The final vertex connects back
        # to the first vertex.
        #
        for i in range(len(vertices)):

            start = vertices[i]

            end = vertices[
                (i + 1) % len(vertices)
            ]

            edges.append(
                LineString(
                    [
                        (
                            start.x,
                            start.y,
                        ),
                        (
                            end.x,
                            end.y,
                        ),
                    ]
                )
            )

        return edges