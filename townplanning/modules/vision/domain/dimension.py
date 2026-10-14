from __future__ import annotations

from dataclasses import dataclass

from .line import Line


@dataclass(slots=True)
class Dimension:

    line: Line

    value: float

    unit: str

    confidence: float = 1.0

    @property
    def metric_value(self) -> float:

        if self.unit.lower() in (
            "m",
            "meter",
            "meters",
        ):
            return self.value

        if self.unit.lower() in (
            "mm",
            "millimeter",
        ):
            return self.value / 1000

        if self.unit.lower() in (
            "cm",
        ):
            return self.value / 100

        return self.value