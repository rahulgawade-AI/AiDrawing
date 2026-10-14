from __future__ import annotations

from dataclasses import dataclass, field

from townplanning.modules.vision.domain.boundary import Boundary
from townplanning.modules.vision.domain.point import Point


@dataclass(slots=True)
class PlotBoundary:
    """
    Represents the legal boundary of a land parcel.

    The boundary may consist of straight lines,
    arcs and polylines.
    """

    boundary: Boundary

    survey_number: str | None = None

    cts_number: str | None = None

    plot_number: str | None = None

    area: float | None = None

    perimeter: float | None = None

    centroid: Point | None = None

    road_frontages: list[int] = field(default_factory=list)

    north_angle: float | None = None

    metadata: dict = field(default_factory=dict)