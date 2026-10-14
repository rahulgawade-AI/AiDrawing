from __future__ import annotations


class UnitConverter:

    def to_meter(
        self,
        value: float,
        unit: str,
    ) -> float:

        unit = unit.lower()

        if unit in ("m", "meter", "meters"):
            return value

        if unit in ("cm",):
            return value / 100

        if unit in ("mm",):
            return value / 1000

        if unit in ("ft", "feet"):
            return value * 0.3048

        if unit in ("inch", "in"):
            return value * 0.0254

        return value