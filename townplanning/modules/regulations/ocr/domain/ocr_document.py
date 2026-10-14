"""
OCR Document Domain Model.
"""

from dataclasses import dataclass, field

from townplanning.modules.regulations.ocr.domain.ocr_page import OCRPage


@dataclass(slots=True)
class OCRDocument:
    """
    Represents the complete OCR output for a PDF.
    """

    source: str

    pages: list[OCRPage] = field(default_factory=list)

    metadata: dict = field(default_factory=dict)

    def add_page(
        self,
        page: OCRPage,
    ) -> None:
        self.pages.append(page)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def block_count(self) -> int:
        return sum(
            len(page.blocks)
            for page in self.pages
        )