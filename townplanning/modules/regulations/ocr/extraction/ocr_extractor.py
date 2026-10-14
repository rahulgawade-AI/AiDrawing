"""
OCR Extractor.

High-level entry point for OCR extraction from PDF documents.
"""

from __future__ import annotations

import logging
from pathlib import Path

from townplanning.modules.regulations.ocr.domain.ocr_block import OCRBlock
from townplanning.modules.regulations.ocr.services.ocr_service import OCRService

logger = logging.getLogger(__name__)


class OCRExtractor:
    """
    High-level OCR extraction component.
    """

    def __init__(
        self,
        service: OCRService,
    ) -> None:

        self.service = service

    def extract(
        self,
        pdf_path: str | Path,
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> list[OCRBlock]:
        """
        Extract OCR from a PDF.

        If start_page/end_page are supplied, only those pages are
        processed.
        """

        logger.info(
            "Starting OCR extraction for %s",
            pdf_path,
        )

        try:

            blocks = self.service.extract(
                pdf_path=pdf_path,
                start_page=start_page,
                end_page=end_page,
            )

            logger.info(
                "OCR extraction completed (%d blocks).",
                len(blocks),
            )

            return blocks

        except Exception:

            logger.exception(
                "OCR extraction failed."
            )

            return []

    def extract_page(
        self,
        pdf_path: str | Path,
        page: int,
    ) -> list[OCRBlock]:

        try:

            return self.service.extract_page(
                pdf_path,
                page,
            )

        except Exception:

            logger.exception(
                "OCR failed on page %d",
                page,
            )

            return []

    def is_supported(
        self,
        pdf_path: str | Path,
    ) -> bool:

        return Path(pdf_path).suffix.lower() == ".pdf"