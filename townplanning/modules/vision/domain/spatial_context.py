from __future__ import annotations

from dataclasses import dataclass, field

from shapely.geometry import LineString
from typing import Any

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
from townplanning.modules.vision.domain.plot_number import (
    PlotNumber,
)
from townplanning.modules.vision.domain.road import (
    Road,
)
from townplanning.modules.vision.domain.scale import (
    Scale,
)
from townplanning.modules.vision.domain.text_block import (
    TextBlock,
)


@dataclass(slots=True)
class SpatialContext:
    """
    Final spatial representation produced by
    the Vision module.

    This object is consumed by the
    Engineering / Rule Engine.
    """

    boundary: PlotBoundary

    roads: list[Road] = field(
        default_factory=list
    )

    north: NorthArrow | None = None

    scale: Scale | None = None

    area: PlotArea | None = None

    plot_number: PlotNumber | None = None

    dimensions: list[Dimension] = field(
        default_factory=list
    )

    texts: list[TextBlock] = field(
        default_factory=list
    )

    edges: list[LineString] = field(
        default_factory=list
    )

    edge_dimensions: list = field(
        default_factory=list
    )

    edge_roads: list = field(
        default_factory=list
    )

    internal_text: list[TextBlock] = field(
        default_factory=list
    )

    external_text: list[TextBlock] = field(
        default_factory=list
    )
    vision_evidence: Any | None = None