from pathlib import Path
from dataclasses import asdict

from townplanning.modules.regulations.ocr.extraction.ocr_extractor import (
    OCRExtractor,
)
from townplanning.modules.regulations.ocr.ingestion.ocr_dom_builder import (
    OCRDOMBuilder,
)
from townplanning.modules.regulations.ocr.providers.surya_provider import (
    SuryaProvider,
)
from townplanning.modules.regulations.ocr.services.inference_manager import (
    SuryaInferenceManager,
)
from townplanning.modules.regulations.ocr.services.ocr_service import (
    OCRService,
)
from townplanning.modules.regulations.ocr.services.page_renderer import (
    PageRenderer,
)

PDF = Path("data/regulations/UDCPR.pdf")

PAGE = 441


def test_single_page_ocr():

    assert PDF.exists()

    inference_manager = SuryaInferenceManager()

    provider = SuryaProvider(
        inference_manager=inference_manager,
    )

    renderer = PageRenderer()

    ocr_service = OCRService(
        provider=provider,
        renderer=renderer,
    )

    extractor = OCRExtractor(
        service=ocr_service,
    )

    dom_builder = OCRDOMBuilder()

    print()
    print("=" * 80)
    print(f"OCR PAGE {PAGE}")
    print("=" * 80)

    print("Running OCR...")

    blocks = extractor.extract(
        PDF,
        start_page=PAGE,
        end_page=PAGE,
    )

    print(f"Blocks Extracted : {len(blocks)}")

    assert blocks

    document = dom_builder.build(
        blocks,
        source=str(PDF),
    )

    assert len(document.pages) == 1

    page = document.pages[0]

    print()
    print("=" * 80)
    print(f"Page Number : {page.page_number}")
    print(f"Blocks      : {len(page.blocks)}")
    print("=" * 80)

    total_chars = 0

    print()
    print("=" * 100)
    print("PAGE CONTENT")
    print("=" * 100)

    page_text = []

    for block in page.blocks:

        if block.text.strip():
            print(block.text)
            page_text.append(block.text)

    full_text = "\n".join(page_text)

    print()
    print("=" * 100)
    print("FULL PAGE TEXT")
    print("=" * 100)

    print(full_text)

    print()
    print("=" * 100)
    print(f"Total Blocks     : {len(page.blocks)}")
    print(f"Total Characters : {len(full_text)}")
    print("=" * 100)