"""
Production PDF Reader.

Responsibilities
----------------
- Open PDF
- Read pages
- Return raw UTF-8 text

No AI.
No preprocessing.
No cleaning.
"""

from pathlib import Path

import fitz


class PDFReader:

    def __init__(self):

        self._document = None

        self._path = None

    # --------------------------------------------------

    def open(
        self,
        pdf_path: str,
    ):

        path = Path(pdf_path)

        if not path.exists():

            raise FileNotFoundError(path)

        try:

            self._document = fitz.open(path)

        except Exception as exc:

            raise ValueError(
                f"Cannot open PDF: {path}"
            ) from exc

        self._path = path

        return self

    # --------------------------------------------------

    @property
    def page_count(self):

        if self._document is None:

            raise RuntimeError(
                "PDF not opened."
            )

        return len(self._document)

    # --------------------------------------------------

    def page(
        self,
        page_number: int,
    ) -> str:

        if self._document is None:

            raise RuntimeError(
                "PDF not opened."
            )

        if page_number < 1:

            raise ValueError(
                "Pages start from 1."
            )

        if page_number > self.page_count:

            raise ValueError(
                f"Page {page_number} "
                "does not exist."
            )

        page = self._document.load_page(
            page_number - 1
        )

        return page.get_text("text")

    # --------------------------------------------------

    def pages(self):

        if self._document is None:

            raise RuntimeError(
                "PDF not opened."
            )

        for page_number in range(
            1,
            self.page_count + 1,
        ):

            yield page_number, self.page(
                page_number
            )

    # --------------------------------------------------

    def close(self):

        if self._document:

            self._document.close()

            self._document = None