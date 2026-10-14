from __future__ import annotations

import cv2

from townplanning.modules.vision.domain.boundary import Boundary
from townplanning.modules.vision.domain.geometry import GeometryModel
from townplanning.modules.vision.domain.point import Point
from townplanning.modules.vision.domain.polyline import Polyline
from townplanning.modules.vision.domain.region import Region


class GeometryBuilder:
    """
    Converts raw OpenCV output into domain geometry.
    """

    def build(
        self,
        *,
        lines,
        arcs,
        circles,
        contours,
    ) -> GeometryModel:

        geometry = GeometryModel()

        geometry.lines.extend(lines)

        geometry.arcs.extend(arcs)

        geometry.circles.extend(circles)

        for contour in contours:

            epsilon = 0.003 * cv2.arcLength(
                contour,
                True,
            )

            approx = cv2.approxPolyDP(
                contour,
                epsilon,
                True,
            )

            polyline = Polyline(
                points=[
                    Point(
                        float(pt[0][0]),
                        float(pt[0][1]),
                    )
                    for pt in approx
                ],
                closed=True,
            )

            geometry.polylines.append(polyline)

            boundary = Boundary(
                segments=[polyline]
            )

            geometry.boundaries.append(boundary)

            geometry.regions.append(
                Region(
                    outer=boundary,
                )
            )

        return geometry