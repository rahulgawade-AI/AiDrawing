from pathlib import Path
import traceback

from townplanning.infrastructure.database.session import SessionLocal

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
from townplanning.modules.regulations.ocr.services.ocr_document_persistence_service import (
    OCRDocumentPersistenceService,
)

from townplanning.infrastructure.database.repositories.sqlalchemy_ocr_repository import (
    SQLAlchemyOCRRepository,
)

PDF = Path("data/regulations/UDCPR.pdf")

OCR_START_PAGE = 442
OCR_END_PAGE = 511      # Test one page first


def test_ocr_ingestion():

    assert PDF.exists()

    session = SessionLocal()

    try:

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

        ocr_repository = SQLAlchemyOCRRepository(session)

        persistence_service = OCRDocumentPersistenceService(
            repository=ocr_repository,
        )

        total_inserted = 0
        verified = 0

        print("=" * 80)
        print("Starting OCR ingestion")
        print(f"Pages : {OCR_START_PAGE} -> {OCR_END_PAGE}")
        print("=" * 80)

        for page in range(OCR_START_PAGE, OCR_END_PAGE + 1):

            print()
            print("=" * 80)
            print(f"PAGE {page}")
            print("=" * 80)

            try:

                #
                # Skip already processed pages
                #
                if ocr_repository.exists(
                    source=str(PDF),
                    page_number=page,
                ):
                    print(f"[{page}] Already processed - skipping")
                    verified += 1
                    continue

                #
                # OCR Extraction
                #
                print(f"[{page}] Running OCR...")

                blocks = extractor.extract(
                    PDF,
                    start_page=page,
                    end_page=page,
                )

                print(f"[{page}] Extracted {len(blocks)} OCR blocks")

                if not blocks:
                    print(f"[{page}] No OCR blocks found")
                    continue

                #
                # Build OCR Document
                #
                document = dom_builder.build(
                    blocks,
                    source=str(PDF),
                )

                print(
                    f"[{page}] OCR Document contains "
                    f"{len(document.pages)} page(s)"
                )

                #
                # Persist
                #
                inserted = persistence_service.persist(document)

                session.commit()

                total_inserted += inserted

                print(
                    f"[{page}] Inserted {inserted} OCR document(s)"
                )

                #
                # Verify
                #
                stored = ocr_repository.get_by_page(
                    source=str(PDF),
                    page_number=page,
                )

                if stored is None:
                    print(f"[{page}] FAILED - OCR document not stored")
                    continue

                print(f"[{page}] OCR document stored successfully")

                print(
                    f"[{page}] Text Length : "
                    f"{len(stored.original_text)} characters"
                )

                verified += 1

            except Exception:

                session.rollback()

                print(f"[{page}] FAILED")
                traceback.print_exc()

                continue

        print()
        print("=" * 80)
        print("OCR INGESTION SUMMARY")
        print("=" * 80)

        print(f"Pages processed : {OCR_END_PAGE - OCR_START_PAGE + 1}")
        print(f"Pages stored    : {verified}")
        print(f"Documents saved : {total_inserted}")

        assert verified > 0

    finally:
        session.close()