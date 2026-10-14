from __future__ import annotations

from dataclasses import dataclass, field

from .polyline import Polyline


@dataclass(slots=True)
class Road:
    """
    Represents a road detected adjacent to the site.
    """

    name: str | None = None

    width: float | None = None

    unit: str = "m"

    centerline: Polyline | None = None

    road_type: str | None = None

    remarks: str | None = None

    metadata: dict = field(default_factory=dict)