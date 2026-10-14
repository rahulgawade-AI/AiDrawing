from __future__ import annotations

from dataclasses import dataclass

from townplanning.modules.vision.domain.point import Point


@dataclass(slots=True)
class NorthArrow:
    """
    Represents the detected north arrow in a site plan.
    """

    center: Point

    angle: float
    """
    Angle in degrees.

    0°   -> North (Up)

    90°  -> East

    180° -> South

    270° -> West
    """

    confidence: float = 1.0

    detected_text: str | None = None

    source: str = "vision"

    @property
    def is_valid(self) -> bool:
        return self.confidence >= 0.50

    @property
    def bearing(self) -> float:
        """
        Returns normalized bearing (0-360°).
        """
        return self.angle % 360

    def __str__(self) -> str:
        return (
            f"NorthArrow("
            f"angle={self.bearing:.2f}°, "
            f"confidence={self.confidence:.2f})"
        )