from __future__ import annotations

import re

from townplanning.modules.vision.detectors.base_detector import BaseDetector
from townplanning.modules.vision.domain.drawing import Drawing
from townplanning.modules.vision.domain.line import Line
from townplanning.modules.vision.domain.point import Point
from townplanning.modules.vision.domain.road import Road


class RoadDetector(BaseDetector):

    ROAD_REGEX = re.compile(
        r"(\d+(?:\.\d+)?)\s*(M|METER|METRE).*(ROAD)",
        re.IGNORECASE,
    )

    def detect(
        self,
        drawing: Drawing,
    ) -> list[Road]:

        roads = []

        for page in drawing.pages:

            for block in page.texts:

                match = self.ROAD_REGEX.search(block.text)

                if not match:
                    continue

                width = float(match.group(1))

                center = block.bounding_box.center

                roads.append(
                    Road(
                        centerline=Line(
                            Point(center.x-100, center.y),
                            Point(center.x+100, center.y),
                        ),
                        width=width,
                        name=block.text,
                    )
                )

        return roads