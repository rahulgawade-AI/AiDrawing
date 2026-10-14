from pathlib import Path

from townplanning.modules.regulations.ingestion.pdf_reader import (
    PDFReader,
)

from townplanning.modules.regulations.ingestion.page_window import (
    PageWindowBuilder,
)


PDF = Path(
    "data/regulations/UDCPR.pdf"
)


def test_page_window():

    reader = PDFReader().open(PDF)

    builder = PageWindowBuilder(reader)

    window = builder.build(85)

    assert window.previous_page == 84

    assert window.current_page == 85

    assert window.next_page == 86

    assert len(window.previous_text) > 100

    assert len(window.current_text) > 100

    assert len(window.next_text) > 100

    reader.close()