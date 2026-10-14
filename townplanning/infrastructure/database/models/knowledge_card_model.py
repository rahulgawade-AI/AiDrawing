from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from townplanning.infrastructure.database.base import Base


class KnowledgeCardModel(Base):

    __tablename__ = "knowledge_cards"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    regulation_id: Mapped[str] = mapped_column(
        ForeignKey("regulations.id"),
        nullable=False,
        index=True,
    )

    title: Mapped[str]

    summary: Mapped[str]

    purpose: Mapped[str]

    scope: Mapped[str]

    definitions: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    permissions: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    conditions: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    prohibitions: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    measurements: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    exceptions: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    applicability: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    authority: Mapped[str]

    inputs: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    outputs: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    references: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    related_regulations: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    keywords: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    examples: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    notes: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    extra_metadata: Mapped[dict] = mapped_column(
    "metadata",      # database column name
    JSONB,
    default=dict,
)