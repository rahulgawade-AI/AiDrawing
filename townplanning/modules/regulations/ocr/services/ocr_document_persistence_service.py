from __future__ import annotations

from townplanning.modules.regulations.ocr.domain.ocr_document import OCRDocument
from townplanning.modules.regulations.ocr.domain.ocr_record import OCRRecord


class OCRDocumentPersistenceService:

    def __init__(
        self,
        repository,
    ):
        self.repository = repository

    def persist(
        self,
        document: OCRDocument,
    ) -> int:

        inserted = 0

        for page in document.pages:

            text = "\n".join(
                block.text.strip()
                for block in page.blocks
                if block.text.strip()
            )

            if not text:
                continue

            record = OCRRecord(
                source=document.source,
                page_number=page.page_number,
                original_text=text,
                metadata={
                    "block_count": len(page.blocks),
                    "engine": "surya",
                },
            )

            self.repository.save(record)

            inserted += 1

        return inserted