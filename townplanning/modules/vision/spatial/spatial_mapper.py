from __future__ import annotations

from townplanning.modules.vision.domain.spatial_context import (
    SpatialContext,
)

from .edge_mapper import EdgeMapper
from .road_association import RoadAssociation
from .dimension_association import (
    DimensionAssociation,
)
from .text_association import (
    TextAssociation,
)
from .north_association import (
    NorthAssociation,
)


class SpatialMapper:
    """
    Performs all spatial associations for the
    Vision module and enriches the SpatialContext.

    This is the final step of Sprint 3.
    Sprint 4 (Engineering) will consume this object.
    """

    def __init__(self):

        self.edge_mapper = EdgeMapper()

        self.dimension_mapper = (
            DimensionAssociation()
        )

        self.road_mapper = (
            RoadAssociation()
        )

        self.text_mapper = (
            TextAssociation()
        )

        self.north_mapper = (
            NorthAssociation()
        )

    def map(
        self,
        context: SpatialContext,
    ) -> SpatialContext:

        #
        # Extract boundary edges
        #
        context.edges = self.edge_mapper.map(
            context.boundary,
        )

        #
        # Associate dimensions with edges
        #
        context.edge_dimensions = (
            self.dimension_mapper.associate(
                context.dimensions,
                context.edges,
            )
        )
        print()
        print("## DIMENSION → EDGE ASSOCIATIONS")

        for index, (
            dimension,
            edge,
        ) in enumerate(
            context.edge_dimensions,
            start=1,
        ):

            print(
                f"{index}. "
                f"{dimension.value} {dimension.unit}"
                f" -> "
                f"{edge.wkt if edge is not None else 'NONE'}"
            )

        #
        # Associate roads with edges
        #
        context.edge_roads = (
            self.road_mapper.associate(
                context.roads,
                context.edges,
            )
        )

        #
        # Classify text blocks
        #
        (
            context.internal_text,
            context.external_text,
        ) = self.text_mapper.associate(
            context.texts,
            context.boundary,
        )

        #
        # Determine site orientation
        #
        if context.north is not None:

            self.north_mapper.associate(
            context.north,
        context.boundary,
    )

        return context