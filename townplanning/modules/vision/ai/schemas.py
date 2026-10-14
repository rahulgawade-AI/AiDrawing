from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AIRoadResult:
    """
    Semantic road detection returned by the AI model.

    Geometry is intentionally not fabricated here.
    """

    road_visible: bool

    road_location: str | None = None

    road_label: str | None = None

    approximate_width: float | None = None

    unit: str = "m"

    confidence: float = 0.0

    raw_response: dict | None = None
