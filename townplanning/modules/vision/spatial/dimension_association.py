from __future__ import annotations

from math import acos
from math import degrees

from shapely.geometry import LineString
from shapely.geometry import Point as ShapelyPoint

from townplanning.modules.vision.domain.dimension import (
    Dimension,
)


class DimensionAssociation:
    """
    Associates dimensions with the most likely plot edge.

    Association is based on:

        1. Dimension / edge orientation
        2. Perpendicular distance
        3. Projection overlap
        4. Combined geometric score

    The public interface intentionally remains:

        list[
            tuple[
                Dimension,
                LineString | None,
            ]
        ]
    """

    #
    # Maximum useful distance between a dimension
    # midpoint and an edge.
    #
    MAX_DISTANCE = 180.0

    #
    # Minimum score required before accepting
    # an edge association.
    #
    MIN_SCORE = 0.20

    def associate(
        self,
        dimensions: list[Dimension],
        edges: list[LineString],
    ) -> list[
        tuple[
            Dimension,
            LineString | None,
        ]
    ]:

        associations: list[
            tuple[
                Dimension,
                LineString | None,
            ]
        ] = []

        for dimension in dimensions:

            best_edge: LineString | None = None

            best_score = float("-inf")

            #
            # Evaluate every boundary edge.
            #
            for edge in edges:

                score = self._score(
                    dimension,
                    edge,
                )

                if score > best_score:

                    best_score = score

                    best_edge = edge

            #
            # Reject an edge if no sufficiently
            # strong association was found.
            #
            if best_score < self.MIN_SCORE:

                best_edge = None

            associations.append(
                (
                    dimension,
                    best_edge,
                )
            )

        return associations

    # ======================================================
    # SCORE
    # ======================================================

    def _score(
        self,
        dimension: Dimension,
        edge: LineString,
    ) -> float:
        """
        Calculate geometric compatibility between
        a dimension and an edge.
        """

        if edge.is_empty:

            return float("-inf")

        #
        # --------------------------------------------------
        # Dimension line
        # --------------------------------------------------
        #

        dimension_start = (
            dimension.line.start
        )

        dimension_end = (
            dimension.line.end
        )

        dimension_dx = (
            dimension_end.x
            - dimension_start.x
        )

        dimension_dy = (
            dimension_end.y
            - dimension_start.y
        )

        dimension_length = (
            dimension_dx ** 2
            + dimension_dy ** 2
        ) ** 0.5

        #
        # Invalid/zero-length dimension.
        #
        if dimension_length <= 0:

            return float("-inf")

        #
        # --------------------------------------------------
        # Edge coordinates
        # --------------------------------------------------
        #

        edge_start = edge.coords[0]

        edge_end = edge.coords[-1]

        edge_dx = (
            edge_end[0]
            - edge_start[0]
        )

        edge_dy = (
            edge_end[1]
            - edge_start[1]
        )

        edge_length = (
            edge_dx ** 2
            + edge_dy ** 2
        ) ** 0.5

        #
        # Invalid edge.
        #
        if edge_length <= 0:

            return float("-inf")

        #
        # --------------------------------------------------
        # 1. Orientation score
        # --------------------------------------------------
        #

        dot = (
            dimension_dx * edge_dx
            + dimension_dy * edge_dy
        )

        cosine = abs(
            dot
            / (
                dimension_length
                * edge_length
            )
        )

        cosine = max(
            0.0,
            min(1.0, cosine),
        )

        orientation_difference = degrees(
            acos(cosine)
        )

        #
        # Parallel:
        #
        # 0°   -> score 1.0
        # 30°  -> score ~0.866
        # 45°  -> score ~0.707
        # 90°  -> score 0.0
        #
        orientation_score = cosine

        #
        # --------------------------------------------------
        # 2. Dimension midpoint
        # --------------------------------------------------
        #

        midpoint_x = (
            dimension_start.x
            + dimension_end.x
        ) / 2.0

        midpoint_y = (
            dimension_start.y
            + dimension_end.y
        ) / 2.0

        midpoint = ShapelyPoint(
            midpoint_x,
            midpoint_y,
        )

        #
        # --------------------------------------------------
        # 3. Distance score
        # --------------------------------------------------
        #

        distance = edge.distance(
            midpoint
        )

        #
        # Too far away to be a useful candidate.
        #
        if distance > self.MAX_DISTANCE:

            return float("-inf")

        distance_score = max(
            0.0,
            1.0
            - (
                distance
                / self.MAX_DISTANCE
            ),
        )

        #
        # --------------------------------------------------
        # 4. Projection overlap
        # --------------------------------------------------
        #

        projection_score = (
            self._projection_overlap(
                dimension_start.x,
                dimension_start.y,
                dimension_end.x,
                dimension_end.y,
                edge_start[0],
                edge_start[1],
                edge_end[0],
                edge_end[1],
            )
        )

        #
        # --------------------------------------------------
        # 5. Final weighted score
        # --------------------------------------------------
        #
        # Orientation is strongest because a horizontal
        # dimension should normally match a horizontal-ish
        # boundary edge.
        #
        # Distance is next.
        #
        # Projection overlap helps distinguish nearby
        # but unrelated edges.
        #
        #

        score = (
            orientation_score * 0.45
            + distance_score * 0.35
            + projection_score * 0.20
        )

        #
        # OCR confidence provides a small final adjustment.
        #
        confidence = max(
            0.0,
            min(
                1.0,
                float(dimension.confidence),
            ),
        )

        score *= (
            0.90
            + 0.10 * confidence
        )

        return score

    # ======================================================
    # PROJECTION OVERLAP
    # ======================================================

    @staticmethod
    def _projection_overlap(
        dimension_start_x: float,
        dimension_start_y: float,
        dimension_end_x: float,
        dimension_end_y: float,
        edge_start_x: float,
        edge_start_y: float,
        edge_end_x: float,
        edge_end_y: float,
    ) -> float:
        """
        Calculate how much of the dimension overlaps
        the plot edge when both are projected onto
        the edge's direction.

        Returns:

            0.0 -> no overlap
            1.0 -> complete dimension overlap
        """

        edge_dx = (
            edge_end_x
            - edge_start_x
        )

        edge_dy = (
            edge_end_y
            - edge_start_y
        )

        edge_length = (
            edge_dx ** 2
            + edge_dy ** 2
        ) ** 0.5

        if edge_length <= 0:

            return 0.0

        #
        # Unit vector along edge.
        #
        ux = edge_dx / edge_length

        uy = edge_dy / edge_length

        #
        # Project dimension endpoints.
        #
        dimension_projection_start = (
            dimension_start_x * ux
            + dimension_start_y * uy
        )

        dimension_projection_end = (
            dimension_end_x * ux
            + dimension_end_y * uy
        )

        #
        # Project edge endpoints.
        #
        edge_projection_start = (
            edge_start_x * ux
            + edge_start_y * uy
        )

        edge_projection_end = (
            edge_end_x * ux
            + edge_end_y * uy
        )

        dimension_min = min(
            dimension_projection_start,
            dimension_projection_end,
        )

        dimension_max = max(
            dimension_projection_start,
            dimension_projection_end,
        )

        edge_min = min(
            edge_projection_start,
            edge_projection_end,
        )

        edge_max = max(
            edge_projection_start,
            edge_projection_end,
        )

        #
        # Intersection length.
        #
        overlap = max(
            0.0,
            min(
                dimension_max,
                edge_max,
            )
            - max(
                dimension_min,
                edge_min,
            ),
        )

        dimension_span = (
            dimension_max
            - dimension_min
        )

        if dimension_span <= 0:

            return 0.0

        return min(
            1.0,
            overlap / dimension_span,
        )