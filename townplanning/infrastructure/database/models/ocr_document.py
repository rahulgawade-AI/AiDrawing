from datetime import UTC
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID
from townplanning.infrastructure.database.base import Base


class OCRDocumentModel(Base):

    __tablename__ = "ocr_documents"

    id: Mapped[str] = mapped_column(
         UUID(as_uuid=True),
    primary_key=True,
    default=uuid4,
    )

    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(20),
    )

    original_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    translated_text: Mapped[str | None] = mapped_column(
        Text,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )