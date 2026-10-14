import pytest

from townplanning.infrastructure.database.session import SessionLocal

from townplanning.infrastructure.database.repositories.sqlalchemy_ocr_repository import (
    SQLAlchemyOCRRepository,
)
from townplanning.modules.regulations.translation.providers.ollama_translation_provider import (
    OllamaTranslationProvider,
)


SOURCE = "data/regulations/UDCPR.pdf"

START_PAGE = 441
END_PAGE = 511


@pytest.mark.functional
def test_translate_udcpr():

    session = SessionLocal()

    try:

        repository = SQLAlchemyOCRRepository(session)
        translator = OllamaTranslationProvider()

        translated = 0
        skipped = 0

        print()
        print("=" * 80)
        print("UDCPR TRANSLATION")
        print("=" * 80)

        for page in range(START_PAGE, END_PAGE + 1):

            print()
            print("=" * 80)
            print(f"PAGE {page}")
            print("=" * 80)

            record = repository.get_by_page(
                source=SOURCE,
                page_number=page,
            )

            assert record is not None, f"Page {page} not found"

            if record.translated_text:
                print(f"[{page}] Already translated")
                skipped += 1
                continue

            print(f"[{page}] Original Length : {len(record.original_text)}")

            print(f"[{page}] Translating...")

            translated_text = translator.translate(
                record.original_text
            )

            assert translated_text

            repository.update_translation(
                record.id,
                translated_text,
            )

            session.commit()

            stored = repository.get_by_page(
                source=SOURCE,
                page_number=page,
            )

            assert stored is not None
            assert stored.translated_text == translated_text

            translated += 1

            print(f"[{page}] Translation saved")
            print(f"[{page}] Translation Length : {len(translated_text)}")

        print()
        print("=" * 80)
        print("TRANSLATION SUMMARY")
        print("=" * 80)
        print(f"Pages translated : {translated}")
        print(f"Pages skipped    : {skipped}")
        print(f"Pages processed  : {translated + skipped}")

    finally:
        session.close()