from __future__ import annotations

from shapely.geometry import LineString, Point

from townplanning.modules.vision.domain.road import Road


class RoadAssociation:
    """
    Associates roads with the nearest plot edge.

    Roads detected by AI may initially have semantic
    information but no geometric centerline.

    Such roads are preserved but cannot yet be associated
    with a specific edge.
    """

    def associate(
        self,
        roads: list[Road],
        edges: list[LineString],
    ) -> list[tuple[Road, LineString | None]]:

        associations: list[
            tuple[Road, LineString | None]
        ] = []

        for road in roads:

            #
            # No geometry yet.
            #
            if road.centerline is None:

                associations.append(
                    (
                        road,
                        None,
                    )
                )

                continue

            #
            # Convert domain Polyline into
            # Shapely LineString.
            #
            points = road.centerline.points

            if len(points) < 2:

                associations.append(
                    (
                        road,
                        None,
                    )
                )

                continue

            road_line = LineString(
                [
                    point.to_tuple()
                    for point in points
                ]
            )

            #
            # Find nearest plot edge.
            #
            nearest_edge = None

            nearest_distance = float("inf")

            for edge in edges:

                distance = edge.distance(
                    road_line
                )

                if distance < nearest_distance:

                    nearest_distance = distance

                    nearest_edge = edge

            associations.append(
                (
                    road,
                    nearest_edge,
                )
            )

        return associations