from __future__ import annotations

from townplanning.modules.vision.detectors.base_detector import BaseDetector
from townplanning.modules.vision.domain.drawing import Drawing


class WallDetector(BaseDetector):
    """
    Detect walls.

    Sprint 3:
        OpenCV Hough Lines

    Future:
        Deep Learning
    """

    def detect(
        self,
        drawing: Drawing,
    ) -> list:

        return []