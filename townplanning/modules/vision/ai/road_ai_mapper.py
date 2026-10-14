from __future__ import annotations

from townplanning.modules.vision.domain.road import Road

from .schemas import AIRoadResult


class RoadAIMapper:
    """
    Converts semantic AI road detections into
    domain Road objects.

    Geometry is intentionally left as None until
    the geometry detector determines the actual
    road centerline.
    """

    def map(
        self,
        detections: list[AIRoadResult],
    ) -> list[Road]:

        roads: list[Road] = []

        for detection in detections:

            if not detection.road_visible:
                continue

            road = Road(
                name=detection.road_label,
                width=detection.approximate_width,
                unit=detection.unit,
                centerline=None,
                road_type="road",
                remarks=(
                    detection.road_location
                ),
                metadata={
                    "detection_source": "ollama",
                    "ai_confidence": (
                        detection.confidence
                    ),
                    "location": (
                        detection.road_location
                    ),
                    "ai_result": (
                        detection.raw_response
                    ),
                },
            )

            roads.append(road)

        return roads
