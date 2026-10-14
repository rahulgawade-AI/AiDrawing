"""
Surya OCR Provider.

Runs the complete OCR pipeline:

Image
    ↓
Layout Detection
    ↓
OCR Recognition
    ↓
OCRBlock Mapping
"""

from __future__ import annotations

import logging

from PIL import Image

from townplanning.modules.regulations.ocr.domain.ocr_block import OCRBlock
from townplanning.modules.regulations.ocr.mappers.surya_mapper import SuryaMapper
from townplanning.modules.regulations.ocr.providers.base import OCRProvider
from townplanning.modules.regulations.ocr.services.inference_manager import (
    SuryaInferenceManager,
)

logger = logging.getLogger(__name__)


class SuryaProvider(OCRProvider):
    """
    Production OCR provider using Surya.
    """

    def __init__(
        self,
        inference_manager: SuryaInferenceManager | None = None,
    ) -> None:

        self.inference_manager = (
            inference_manager
            if inference_manager is not None
            else SuryaInferenceManager()
        )

        self.mapper = SuryaMapper()

    @property
    def name(self) -> str:
        return "surya"

    def initialize(self) -> None:
        """
        Initialize Surya models.
        Safe to call multiple times.
        """
        self.inference_manager.initialize()

    def shutdown(self) -> None:
        """
        Release model resources.
        """
        self.inference_manager.shutdown()

    def supports_language(
        self,
        language: str,
    ) -> bool:
        """
        Surya supports multilingual OCR.
        """
        return True

    def extract(
        self,
        image: Image.Image,
        page: int,
    ) -> list[OCRBlock]:
        """
        Run OCR on a single page image.
        """

        self.initialize()

        logger.info(
            "Running OCR on page %d",
            page,
        )

        #
        # Layout Detection
        #
        layout_predictor = self.inference_manager.layout

        if layout_predictor is None:
            raise RuntimeError(
                "Layout predictor not initialized."
            )

        layout_results = layout_predictor([image])

        if not layout_results:
            logger.warning(
                "No layout detected on page %d",
                page,
            )
            return []

        #
        # OCR Recognition
        #
        recognition_predictor = self.inference_manager.recognition

        if recognition_predictor is None:
            raise RuntimeError(
                "Recognition predictor not initialized."
            )

        recognition_results = recognition_predictor(
            [image],
            layout_results,
        )

        if not recognition_results:
            logger.warning(
                "No OCR results for page %d",
                page,
            )
            return []

        #
        # Convert Surya output to OCRBlock
        #
        blocks = self.mapper.map(
            page=page,
            results=recognition_results,
        )

        logger.info(
            "Extracted %d OCR blocks from page %d",
            len(blocks),
            page,
        )

        return blocks