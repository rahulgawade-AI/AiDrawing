"""
PDF Page Renderer.

Responsible for converting PDF pages into PIL images for OCR.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fitz
from PIL import Image

logger = logging.getLogger(__name__)


class PageRenderer:
    """
    Renders PDF pages as high-resolution PIL images.
    """

    def __init__(
        self,
        dpi: int = 300,
    ) -> None:

        self.dpi = dpi
        self.zoom = dpi / 72.0

    def render(
        self,
        pdf_path: str | Path,
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> list[Image.Image]:
        """
        Render a PDF or a page range.

        Parameters
        ----------
        pdf_path
            PDF file.

        start_page
            First page (1-based). None = first page.

        end_page
            Last page (1-based). None = last page.
        """

        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        images: list[Image.Image] = []

        with fitz.open(pdf_path) as document:

            total_pages = document.page_count

            #
            # Default values
            #
            if start_page is None:
                start_page = 1

            if end_page is None:
                end_page = total_pages

            #
            # Validate
            #
            if start_page < 1:
                raise ValueError("start_page must be >= 1")

            if end_page > total_pages:
                raise ValueError(
                    f"end_page ({end_page}) exceeds document page count ({total_pages})"
                )

            if start_page > end_page:
                raise ValueError("start_page must be <= end_page")

            logger.info(
                "Rendering pages %d-%d of %d",
                start_page,
                end_page,
                total_pages,
            )

            #
            # PyMuPDF uses zero-based page indices.
            #
            for page_index in range(start_page - 1, end_page):

                page = document.load_page(page_index)

                images.append(
                    self.render_page(page)
                )

        logger.info(
            "Rendered %d page(s).",
            len(images),
        )

        return images

    def render_page(
        self,
        page: fitz.Page,
    ) -> Image.Image:

        matrix = fitz.Matrix(
            self.zoom,
            self.zoom,
        )

        pixmap = page.get_pixmap(
            matrix=matrix,
            alpha=False,
        )

        return Image.frombytes(
            "RGB",
            (pixmap.width, pixmap.height),
            pixmap.samples,
        )

    def render_page_number(
        self,
        pdf_path: str | Path,
        page_number: int,
    ) -> Image.Image:
        """
        Render a single page.

        Parameters
        ----------
        page_number
            1-based page number.
        """

        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        with fitz.open(pdf_path) as document:

            if page_number < 1 or page_number > document.page_count:
                raise IndexError(
                    f"Invalid page number: {page_number}"
                )

            page = document.load_page(page_number - 1)

            return self.render_page(page)