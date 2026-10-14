from __future__ import annotations

import cv2
import numpy as np

from townplanning.modules.vision.domain.line import Line
from townplanning.modules.vision.domain.point import Point


class LineDetector:

    def detect(
        self,
        image: np.ndarray,
    ) -> list[Line]:

        detected = cv2.HoughLinesP(
            image,
            rho=1,
            theta=np.pi / 180,
            threshold=100,
            minLineLength=40,
            maxLineGap=8,
        )

        if detected is None:
            return []

        lines = []

        for line in detected:

            x1, y1, x2, y2 = line[0]

            lines.append(
                Line(
                    start=Point(x1, y1),
                    end=Point(x2, y2),
                )
            )

        return lines