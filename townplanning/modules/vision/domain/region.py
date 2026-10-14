from __future__ import annotations

from dataclasses import dataclass, field

from .boundary import Boundary


@dataclass(slots=True)
class Region:
    """
    Closed region.
    """

    outer: Boundary

    holes: list[Boundary] = field(default_factory=list)