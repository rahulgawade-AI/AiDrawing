from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VisionObservation:
    """
    Generic observation extracted from an image.

    This class represents WHAT was observed.
    It does not decide whether the observation is a
    planning/regulatory fact.
    """

    observation_type: str
    value: Any = None

    confidence: float = 0.0

    source: str = ""
    source_detail: str = ""

    unit: str | None = None

    bbox: tuple[float, float, float, float] | None = None

    geometry: Any = None

    text: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_type": self.observation_type,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            "source_detail": self.source_detail,
            "unit": self.unit,
            "bbox": self.bbox,
            "geometry": self.geometry,
            "text": self.text,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class VisionEvidence:
    """
    Collection of observations produced by the Vision system.
    """

    observations: list[VisionObservation] = field(default_factory=list)

    image_type: str = "unknown"
    image_type_confidence: float = 0.0

    width: int | None = None
    height: int | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, observation: VisionObservation) -> None:
        self.observations.append(observation)

    def add_many(self, observations: list[VisionObservation]) -> None:
        self.observations.extend(observations)

    def by_type(self, observation_type: str) -> list[VisionObservation]:
        return [
            x
            for x in self.observations
            if x.observation_type == observation_type
        ]

    def best(self, observation_type: str) -> VisionObservation | None:
        matches = self.by_type(observation_type)

        if not matches:
            return None

        return max(
            matches,
            key=lambda x: x.confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_type": self.image_type,
            "image_type_confidence": self.image_type_confidence,
            "width": self.width,
            "height": self.height,
            "observations": [
                x.to_dict()
                for x in self.observations
            ],
            "metadata": self.metadata,
        }