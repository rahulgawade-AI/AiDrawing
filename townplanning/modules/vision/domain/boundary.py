from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Boundary:
    """
    Plot boundary made of mixed geometry.
    """

    segments: list[Any] = field(default_factory=list)