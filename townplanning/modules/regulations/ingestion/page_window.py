"""
Builds contextual windows around a page.

Each window contains:

- Previous page
- Current page
- Next page

Additional information (tables, etc.) can be attached later by
the ingestion pipeline.
"""

from dataclasses import dataclass, field

from townplanning.modules.regulations.ingestion.table import (
    ExtractedTable,
)
from townplanning.modules.regulations.ingestion.pdf_reader import (
    PDFReader,
)


@dataclass(slots=True)
class PageWindow:

    previous_page: int | None

    current_page: int

    next_page: int |None

    previous_text: str

    current_text: str

    next_text: str

    # Filled later by TableExtractor
    tables: list[ExtractedTable] = field(default_factory=list)


class PageWindowBuilder:

    def __init__(
        self,
        reader: PDFReader,
    ):

        self.reader = reader

    # ---------------------------------------------------------

    def build(
        self,
        page_number: int,
    ) -> PageWindow:

        previous_page = (
            page_number - 1
            if page_number > 1
            else None
        )

        next_page = (
            page_number + 1
            if page_number < self.reader.page_count
            else None
        )

        previous_text = (
            self.reader.page(previous_page)
            if previous_page
            else ""
        )

        current_text = self.reader.page(
            page_number
        )

        next_text = (
            self.reader.page(next_page)
            if next_page
            else ""
        )

        return PageWindow(

            previous_page=previous_page,

            current_page=page_number,

            next_page=next_page,

            previous_text=previous_text,

            current_text=current_text,

            next_text=next_text,

            tables=[],
        )