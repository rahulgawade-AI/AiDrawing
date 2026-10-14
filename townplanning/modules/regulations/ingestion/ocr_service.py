"""
Production OCR Service.

Responsibilities
----------------
- Extract embedded text from PDF page
- Fallback to OCR when required
- Supports English + Marathi
"""

from __future__ import annotations

import fitz
from PIL import Image
import numpy as np

from paddleocr import PaddleOCR


class OCRService:
    """
    OCR service with automatic fallback.

    Uses PaddleOCR for scanned pages.

    If a page already contains embedded text,
    OCR is skipped.
    """

    def __init__(self):

        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang="en"
        )

    # ---------------------------------------------------------

    def extract_text(
        self,
        page: fitz.Page,
    ) -> str:

        # Try embedded text first
        text = page.get_text("text")

        if len(text.strip()) > 100:
            return text

        # OCR fallback
        return self._ocr_page(page)

    # ---------------------------------------------------------

    def _ocr_page(
        self,
        page: fitz.Page,
    ) -> str:

        pix = page.get_pixmap(
            dpi=300,
            alpha=False,
        )

        image = Image.frombytes(
            "RGB",
            [pix.width, pix.height],
            pix.samples,
        )

        image = np.array(image)

        result = self.ocr.predict(image)

        lines = []

        if not result:
            return ""

        for res in result:

            if "rec_texts" not in res:
                continue

            lines.extend(res["rec_texts"])

        return "\n".join(lines)