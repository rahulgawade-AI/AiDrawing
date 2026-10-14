from __future__ import annotations

from townplanning.modules.vision.domain.dimension import (
    Dimension,
)
from townplanning.modules.vision.domain.north_arrow import (
    NorthArrow,
)
from townplanning.modules.vision.domain.plot_area import (
    PlotArea,
)
from townplanning.modules.vision.domain.plot_boundary import (
    PlotBoundary,
)
from townplanning.modules.vision.domain.road import (
    Road,
)
from townplanning.modules.vision.domain.scale import (
    Scale,
)
from townplanning.modules.vision.domain.spatial_context import (
    SpatialContext,
)
from townplanning.modules.vision.domain.text_block import (
    TextBlock,
)
from townplanning.modules.vision.domain.plot_number import (
    PlotNumber,
)

class SpatialContextBuilder:
    """
    Builds the final SpatialContext.

    This object is the output of Sprint 3 and
    becomes the input to Sprint 4 (Engineering).
    """

    def build(
        self,
        plot: PlotBoundary,
        roads: list[Road],
        north: NorthArrow | None,
        scale: Scale | None,
        area: PlotArea | None,
        plot_number: PlotNumber | None,
        dimensions: list[Dimension],
        texts: list[TextBlock],
    ) -> SpatialContext:

        return SpatialContext(
            boundary=plot,
            roads=roads,
            north=north,
            scale=scale,
            area=area,
            dimensions=dimensions,
            texts=texts,
            plot_number=plot_number,
        )