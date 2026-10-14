from __future__ import annotations

from dataclasses import dataclass, field

from .arc import Arc
from .boundary import Boundary
from .circle import Circle
from .line import Line
from .polyline import Polyline
from .region import Region


@dataclass(slots=True)
class GeometryModel:

    lines: list[Line] = field(default_factory=list)

    arcs: list[Arc] = field(default_factory=list)

    circles: list[Circle] = field(default_factory=list)

    polylines: list[Polyline] = field(default_factory=list)

    boundaries: list[Boundary] = field(default_factory=list)

    regions: list[Region] = field(default_factory=list)