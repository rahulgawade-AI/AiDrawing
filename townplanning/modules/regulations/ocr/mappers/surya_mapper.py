"""
Surya OCR Result Mapper.

Converts Surya OCR objects into OCRBlock domain objects.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from townplanning.modules.regulations.ocr.domain.ocr_block import OCRBlock

logger = logging.getLogger(__name__)


class SuryaMapper:
    """
    Maps Surya OCR results to OCRBlock domain objects.

    This class isolates the rest of the application from
    Surya's internal API and object model.
    """

    ENGINE_NAME = "surya"

    def map(
        self,
        *,
        page: int,
        results: list[Any],
    ) -> list[OCRBlock]:
        """
        Convert PageOCRResult objects into OCRBlocks.
        """

        blocks: list[OCRBlock] = []

        if not results:
            return blocks

        for page_result in results:
            blocks.extend(
                self._map_page(
                    page=page,
                    page_result=page_result,
                )
            )

        logger.debug(
            "Mapped %d OCR blocks from Surya.",
            len(blocks),
        )

        return blocks

    def _map_page(
        self,
        *,
        page: int,
        page_result: Any,
    ) -> list[OCRBlock]:

        blocks: list[OCRBlock] = []

        #
        # Current Surya API returns:
        #
        # PageOCRResult.blocks
        #

        for order, block in enumerate(getattr(page_result, "blocks", [])):

            if getattr(block, "error", False):
                continue

            if getattr(block, "skipped", False):
                continue

            text = self._extract_text(block)

            if not text:
                continue

            #polygon = getattr(block, "polygon", None)

            #bbox = self._polygon_to_bbox(polygon)

            confidence = float(
                getattr(block, "confidence", 1.0)
            )
            polygon = getattr(block, "polygon", None) or []

            blocks.append(
            OCRBlock(
                id=f"{page}-{order}",
        page=page,
        text=text,
        confidence=confidence,
        language="unknown",
        polygon=polygon,
        metadata={
            "engine": self.ENGINE_NAME,
            "label": getattr(block, "label", ""),
            "raw_label": getattr(block, "raw_label", ""),
            "reading_order": getattr(block, "reading_order", order),
        },
    )
)

            # blocks.append(
            #     OCRBlock(
            #         page=page,
            #         text=text,
            #         confidence=confidence,
            #         language="unknown",
            #         bbox=bbox,
            #         metadata={
            #             "engine": self.ENGINE_NAME,
            #             "label": getattr(block, "label", ""),
            #             "raw_label": getattr(block, "raw_label", ""),
            #             "reading_order": getattr(
            #                 block,
            #                 "reading_order",
            #                 order,
            #             ),
            #         },
            #     )
            # )

        return blocks

    def _extract_text(
        self,
        block: Any,
    ) -> str:
        """
        Extract plain text from HTML returned by Surya.
        """

        html = getattr(block, "html", "")

        if not html:
            return ""

        #
        # Strip HTML tags.
        #

        text = re.sub(
            r"<[^>]+>",
            " ",
            html,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    def _polygon_to_bbox(
        self,
        polygon: Any,
    ) -> list[float]:

        if not polygon:
            return []

        #
        # polygon:
        #
        # [
        #   [x1,y1],
        #   [x2,y2],
        #   [x3,y3],
        #   [x4,y4]
        # ]
        #

        xs = [p[0] for p in polygon]

        ys = [p[1] for p in polygon]

        return [
            float(min(xs)),
            float(min(ys)),
            float(max(xs)),
            float(max(ys)),
        ]