from __future__ import annotations

from dataclasses import dataclass

from .point import Point


@dataclass(slots=True)
class Circle:
    """
    Circle primitive.
    """

    center: Point

    radius: float