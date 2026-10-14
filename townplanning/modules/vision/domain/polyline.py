from __future__ import annotations

from dataclasses import dataclass, field

from .point import Point


@dataclass(slots=True)
class Polyline:
    """
    Connected list of points.
    """

    points: list[Point] = field(default_factory=list)

    closed: bool = False