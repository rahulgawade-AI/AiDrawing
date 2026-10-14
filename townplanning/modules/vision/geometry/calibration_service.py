from __future__ import annotations

from townplanning.modules.vision.domain.scale import Scale


class CalibrationService:
    """
    Converts image pixels into real-world units.
    """

    def pixels_to_meter(
        self,
        pixels: float,
        scale: Scale,
        dpi: float = 300,
    ) -> float:

        inches = pixels / dpi

        paper_mm = inches * 25.4

        drawing_mm = paper_mm * scale.ratio

        return drawing_mm / 1000