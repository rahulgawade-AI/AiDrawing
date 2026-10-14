"""
OCR Service.

Coordinates PDF rendering and OCR extraction.
"""

from __future__ import annotations

import logging
from pathlib import Path

from townplanning.modules.regulations.ocr.domain.ocr_block import OCRBlock
from townplanning.modules.regulations.ocr.providers.base import OCRProvider
from townplanning.modules.regulations.ocr.services.page_renderer import (
    PageRenderer,
)

logger = logging.getLogger(__name__)


class OCRService:
    """
    High-level OCR orchestration service.

    Responsibilities
    ----------------
    - Render PDF pages
    - Execute OCR
    - Return OCRBlocks
    """

    def __init__(
        self,
        provider: OCRProvider,
        renderer: PageRenderer | None = None,
    ) -> None:

        self.provider = provider
        self.renderer = renderer or PageRenderer()

    def extract(
        self,
        pdf_path: str | Path,
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> list[OCRBlock]:
        """
        Extract OCR from an entire PDF or a page range.

        Parameters
        ----------
        pdf_path
            PDF file.

        start_page
            First page (1-based). None = first page.

        end_page
            Last page (1-based). None = last page.
        """

        logger.info(
            "Starting OCR for %s (pages %s-%s)",
            pdf_path,
            start_page,
            end_page,
        )

        images = self.renderer.render(
            pdf_path=pdf_path,
            start_page=start_page,
            end_page=end_page,
        )

        blocks: list[OCRBlock] = []

        #
        # Determine the real page number
        #
        current_page = start_page if start_page is not None else 1

        for image in images:

            logger.info(
                "Running OCR on page %d",
                current_page,
            )

            page_blocks = self.provider.extract(
                image=image,
                page=current_page,
            )

            blocks.extend(page_blocks)

            current_page += 1

        logger.info(
            "OCR completed. %d blocks extracted.",
            len(blocks),
        )

        return blocks

    def extract_page(
        self,
        pdf_path: str | Path,
        page: int,
    ) -> list[OCRBlock]:
        """
        OCR a single page.
        """

        logger.info(
            "Running OCR on page %d",
            page,
        )

        image = self.renderer.render_page_number(
            pdf_path=pdf_path,
            page_number=page,
        )

        return self.provider.extract(
            image=image,
            page=page,
        )

    def extract_images(
        self,
        images: list,
    ) -> list[OCRBlock]:
        """
        OCR already-rendered images.
        """

        blocks: list[OCRBlock] = []

        for page, image in enumerate(images, start=1):

            page_blocks = self.provider.extract(
                image=image,
                page=page,
            )

            blocks.extend(page_blocks)

        return blocks