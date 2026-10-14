from __future__ import annotations

from pathlib import Path

import numpy as np

from townplanning.modules.vision.geometry.image_processor import (
    ImageProcessor,
)
from townplanning.modules.vision.geometry.edge_detector import (
    EdgeDetector,
)
from townplanning.modules.vision.geometry.line_detector import (
    LineDetector,
)
from townplanning.modules.vision.geometry.contour_detector import (
    ContourDetector,
)
from .geometry_builder import GeometryBuilder


class GeometryService:

    def __init__(self):

        self.processor = ImageProcessor()

        self.edge_detector = EdgeDetector()

        self.line_detector = LineDetector()

        self.contour_detector = ContourDetector()

        self.builder = GeometryBuilder()

    def process(
        self,
        image: str | Path | np.ndarray,
    ):

        #
        # Load image.
        #
        # ImageProcessor.load() handles both:
        #
        #   Path / str
        #   numpy.ndarray
        #
        image_data = self.processor.load(
            image
        )

        #
        # Grayscale
        #
        gray = self.processor.grayscale(
            image_data
        )

        #
        # Denoise
        #
        blur = self.processor.denoise(
            gray
        )

        #
        # Threshold
        #
        binary = self.processor.threshold(
            blur
        )

        #
        # Edge detection
        #
        edges = self.edge_detector.detect(
            binary
        )

        #
        # Line detection
        #
        lines = self.line_detector.detect(
            edges
        )

        #
        # Contour detection
        #
        contours = self.contour_detector.detect(
            binary
        )

        #
        # Build geometry
        #
        geometry = self.builder.build(
            lines=lines,
            arcs=[],
            circles=[],
            contours=contours,
        )

        return geometry