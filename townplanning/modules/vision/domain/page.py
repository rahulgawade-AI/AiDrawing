from __future__ import annotations

from dataclasses import dataclass, field

from .dimension import Dimension
from .text_block import TextBlock


@dataclass(slots=True)
class Page:

    number: int

    width: int

    height: int

    texts: list[TextBlock] = field(default_factory=list)

    dimensions: list[Dimension] = field(default_factory=list)