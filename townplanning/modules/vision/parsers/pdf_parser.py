from __future__ import annotations

from pathlib import Path

import fitz

from townplanning.modules.vision.domain.drawing import Drawing
from townplanning.modules.vision.domain.page import Page
from townplanning.modules.vision.parsers.document_parser import (
    DocumentParser,
)


class PDFParser(DocumentParser):
    """
    Parses PDF drawings.
    """

    def parse(
        self,
        file_path: Path,
    ) -> Drawing:

        pdf = fitz.open(file_path)

        pages = []

        for index, page in enumerate(pdf):

            rect = page.rect

            pages.append(
                Page(
                    number=index + 1,
                    width=int(rect.width),
                    height=int(rect.height),
                )
            )

        drawing = Drawing(
            filename=file_path.name,
            pages=pages,
            metadata={
                "type": "pdf",
                "page_count": len(pages),
            },
        )

        pdf.close()

        return drawing