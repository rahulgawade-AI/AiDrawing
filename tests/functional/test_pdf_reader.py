from pathlib import Path

from townplanning.modules.regulations.ingestion.pdf_reader import (
    PDFReader,
)


PDF = Path(
    "data/regulations/UDCPR.pdf"
)


def test_pdf_reader():

    reader = PDFReader().open(PDF)

    assert reader.page_count > 500

    first_page = reader.page(1)

    assert len(first_page) > 100

    page_number, page = next(reader.pages())

    assert page_number == 1

    assert page == first_page

    reader.close()