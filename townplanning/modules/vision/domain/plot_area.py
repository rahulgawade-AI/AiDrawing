from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PlotArea:
    """
    Represents an area explicitly stated in the drawing.

    Example:
        PLOT AREA
        745.60 SQ.M.
    """

    value: float

    unit: str = "sq.m."

    source_text: str | None = None

    confidence: float = 1.0

    @property
    def metric_value(self) -> float:
        """
        Return area in square metres.
        """

        normalized = self.unit.lower().replace(" ", "")

        if normalized in (
            "sq.m.",
            "sq.m",
            "sqm",
            "m²",
            "m2",
        ):
            return self.value

        if normalized in (
            "sq.ft.",
            "sq.ft",
            "sqft",
            "ft²",
            "ft2",
        ):
            return self.value * 0.092903

        return self.value

    def __str__(self) -> str:
        return f"{self.value} {self.unit}"
