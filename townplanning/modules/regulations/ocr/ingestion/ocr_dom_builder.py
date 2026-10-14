"""
OCR DOM Builder.

Converts OCRBlocks into an OCRDocument hierarchy that can later be
matched against the existing regulation hierarchy.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from townplanning.modules.regulations.ocr.domain.ocr_block import OCRBlock
from townplanning.modules.regulations.ocr.domain.ocr_document import OCRDocument
from townplanning.modules.regulations.ocr.domain.ocr_page import OCRPage

logger = logging.getLogger(__name__)


class OCRDOMBuilder:
    """
    Builds an OCR document hierarchy.

    Input
    -----
    List[OCRBlock]

    Output
    ------
    OCRDocument
        ├── OCRPage
        │      ├── OCRBlock
        │      ├── OCRBlock
        │      └── OCRBlock

    No matching or persistence is performed here.
    """

    def build(
        self,
        blocks: list[OCRBlock],
        source: str,
    ) -> OCRDocument:
        """
        Build OCRDocument.

        Parameters
        ----------
        blocks:
            OCR blocks extracted from the OCR engine.

        Returns
        -------
        OCRDocument
        """

        logger.info(
            "Building OCR DOM from %d OCR blocks.",
            len(blocks),
        )

        pages: dict[int, list[OCRBlock]] = defaultdict(list)

        #
        # Group blocks by page
        #
        for block in blocks:
            pages[block.page].append(block)

        ocr_pages: list[OCRPage] = []

        #
        # Sort pages
        #
        for page_number in sorted(pages):

            page_blocks = sorted(
                pages[page_number],
                key=self._reading_order,
            )

            page = OCRPage(
                page_number=page_number,
                blocks=page_blocks,
            )

            ocr_pages.append(page)

        document = OCRDocument(
            pages=ocr_pages,
            source=source,
        )

        logger.info(
            "OCR DOM created with %d pages.",
            len(document.pages),
        )

        return document

    @staticmethod
    def _reading_order(
        block: OCRBlock,
    ) -> tuple[float, float]:
        """
        Reading order.
    
        Uses the OCR polygon.
        """
    
        if not block.polygon:
            return (0.0, 0.0)
    
        xs = [p[0] for p in block.polygon]
        ys = [p[1] for p in block.polygon]
    
        return (
            min(ys),   # top
            min(xs),   # left
        )

    # def _reading_order(
    #     block: OCRBlock,
    # ) -> tuple[float, float]:
    #     """
    #     Reading order.

    #     Sorts using bounding box position.

    #     Returns
    #     -------
    #     (top, left)
    #     """

    #     if not block.bbox or len(block.bbox) < 4:
    #         return (0.0, 0.0)

    #     #
    #     # bbox = [x1, y1, x2, y2]
    #     #
    #     return (
    #         block.bbox[1],
    #         block.bbox[0],
    #     )