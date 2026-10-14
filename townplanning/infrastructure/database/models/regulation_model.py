"""
SQLAlchemy ORM model for Regulation.
"""

from datetime import UTC
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from townplanning.infrastructure.database.base import Base


class RegulationModel(Base):

    __tablename__ = "regulations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    number: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )

    chapter: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    page_start: Mapped[int] = mapped_column(
        Integer,
    )

    page_end: Mapped[int] = mapped_column(
        Integer,
    )

    source_document: Mapped[str] = mapped_column(
        String(100),
        default="UDCPR",
    )

    version: Mapped[str] = mapped_column(
        String(20),
        default="2020",
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