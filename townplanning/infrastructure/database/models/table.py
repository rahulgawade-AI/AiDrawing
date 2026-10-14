from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from townplanning.infrastructure.database.base import Base
from sqlalchemy.dialects.postgresql import JSONB

class Table(Base):
    __tablename__ = "tables"

    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    regulation_id: Mapped[str] = mapped_column(
        ForeignKey("regulations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    table_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    headers: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    rows: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    markdown: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    extra_metadata: Mapped[dict] = mapped_column(
    "metadata",
    JSONB,
    default=dict,
)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )