from __future__ import annotations

from dataclasses import dataclass

from .point import Point


@dataclass(slots=True)
class Arc:
    """
    Circular arc.
    """

    start: Point

    end: Point

    center: Point

    radius: float

    start_angle: float

    end_angle: float

    clockwise: bool = True