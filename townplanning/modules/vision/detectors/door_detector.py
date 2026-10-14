from __future__ import annotations

from townplanning.modules.vision.detectors.base_detector import BaseDetector
from townplanning.modules.vision.domain.drawing import Drawing


class DoorDetector(BaseDetector):

    def detect(
        self,
        drawing: Drawing,
    ) -> list:

        return []