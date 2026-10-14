from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_UDCPR_PDF = Path(
    "/home/ubuntu/llmproject/udcpr_ai/app/services/UDCPR.pdf"
)
class PDFContextLoader:
    """
    Loads textual evidence from the authoritative UDCPR PDF.

    This class does not interpret regulations.

    It only provides PDF evidence to the LLM.
    """
    

    def __init__(
        self,
        pdf_path: str | Path | None = None,
    ):
        self.pdf_path = (
        Path(pdf_path)
        if pdf_path
        else DEFAULT_UDCPR_PDF
    )

    def load(
        self,
        query_terms: list[str] | None = None,
    ) -> dict[str, Any]:

        if self.pdf_path is None:
            return {
                "status": "not_configured",
                "text": "",
                "pages": [],
            }

        if not self.pdf_path.exists():
            return {
                "status": "not_found",
                "text": "",
                "pages": [],
                "path": str(self.pdf_path),
            }

        try:
            import fitz

        except ImportError:

            return {
                "status": "error",
                "text": "",
                "pages": [],
                "error": (
                    "PyMuPDF is not installed. "
                    "Install with: pip install pymupdf"
                ),
            }

        terms = [
            str(term).lower()
            for term in (query_terms or [])
        ]

        pages = []
        full_text = []

        document = fitz.open(
            str(self.pdf_path)
        )

        try:

            for page_number in range(
                len(document)
            ):

                page = document[
                    page_number
                ]

                text = page.get_text(
                    "text"
                ) or ""

                if not text.strip():
                    continue

                lower_text = text.lower()

                # If no query is supplied, return the page.
                if not terms:
                    matched = True

                else:
                    matched = any(
                        term in lower_text
                        for term in terms
                    )

                if matched:

                    pages.append(
                        {
                            "page": page_number + 1,
                            "text": text,
                        }
                    )

                    full_text.append(
                        f"\n--- PDF PAGE "
                        f"{page_number + 1} ---\n"
                        f"{text}"
                    )

        finally:
            document.close()

        return {
            "status": "loaded",
            "path": str(self.pdf_path),
            "page_count": len(pages),
            "pages": pages,
            "text": "\n".join(full_text),
        }