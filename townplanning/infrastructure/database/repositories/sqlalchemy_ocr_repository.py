from __future__ import annotations

from sqlalchemy import select

from townplanning.modules.regulations.ocr.domain.ocr_record import OCRRecord

from townplanning.infrastructure.database.models.ocr_document import (
    OCRDocumentModel,
)
from uuid import UUID
from sqlalchemy import select, update, or_


class SQLAlchemyOCRRepository:

    def __init__(self, session):
        self.session = session

    def save(
        self,
        record: OCRRecord,
    ) -> None:

        model = OCRDocumentModel(
            id=record.id,
            source=record.source,
            page_number=record.page_number,
            language="unknown",
            original_text=record.original_text,
            translated_text=record.translated_text,
            summary=None,
            metadata_json=record.metadata,
        )

        self.session.add(model)

    def get_by_page(
        self,
        source: str,
        page_number: int,
    ) -> OCRRecord | None:

        model = self.session.scalar(
            select(OCRDocumentModel).where(
                OCRDocumentModel.source == source,
                OCRDocumentModel.page_number == page_number,
            )
        )

        if model is None:
            return None

        return OCRRecord(
            id=model.id,
            source=model.source,
            page_number=model.page_number,
            original_text=model.original_text,
            translated_text=model.translated_text,
            metadata=model.metadata_json or {},
        )

    def list_pages(
        self,
        source: str,
    ) -> list[OCRRecord]:

        models = (
            self.session.scalars(
                select(OCRDocumentModel)
                .where(OCRDocumentModel.source == source)
                .order_by(OCRDocumentModel.page_number)
            )
            .all()
        )

        return [
            OCRRecord(
                id=model.id,
                source=model.source,
                page_number=model.page_number,
                original_text=model.original_text,
                translated_text=model.translated_text,
                metadata=model.metadata_json or {},
            )
            for model in models
        ]

    def exists(
        self,
        source: str,
        page_number: int,
    ) -> bool:

        return (
            self.session.scalar(
                select(OCRDocumentModel).where(
                    OCRDocumentModel.source == source,
                    OCRDocumentModel.page_number == page_number,
                )
            )
            is not None
        )
    
    

    def get_untranslated(
        self,
        limit: int | None = None,
    ) -> list[OCRRecord]:
        stmt = (
            select(OCRDocumentModel)
            .where(
                or_(
                    OCRDocumentModel.translated_text.is_(None),
                    OCRDocumentModel.translated_text == ""
                )
            )
            .order_by(OCRDocumentModel.page_number)
        )
    
        if limit is not None:
            stmt = stmt.limit(limit)
    
        rows = self.session.execute(stmt).scalars().all()
    
        return [
            OCRRecord(
                id=row.id,
                source=row.source,
                page_number=row.page_number,
                original_text=row.original_text,
                translated_text=row.translated_text,
                metadata=row.metadata_json or {},
            )
            for row in rows
        ]
    
    
    def update_translation(
        self,
        document_id: UUID,
        translated_text: str,
    ) -> None:
        stmt = (
            update(OCRDocumentModel)
            .where(OCRDocumentModel.id == document_id)
            .values(
                translated_text=translated_text,
            )
        )
    
        self.session.execute(stmt)

    def list(self) -> list[OCRRecord]:

        rows = (
            self.session.scalars(
                select(OCRDocumentModel)
                .order_by(
                    OCRDocumentModel.source,
                    OCRDocumentModel.page_number,
                )
            )
            .all()
        )

        return [
            OCRRecord(
                id=row.id,
                source=row.source,
                page_number=row.page_number,
                original_text=row.original_text,
                translated_text=row.translated_text,
                metadata=row.metadata_json or {},
            )
            for row in rows
        ]

   