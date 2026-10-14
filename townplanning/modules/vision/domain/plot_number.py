from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PlotNumber:
    """
    Represents a plot / survey number extracted from the drawing.

    Examples:
        78/5
        123
        12A
        45/2A
    """

    value: str
    source_text: str | None = None
    confidence: float = 1.0

    def __str__(self) -> str:
        return self.value
