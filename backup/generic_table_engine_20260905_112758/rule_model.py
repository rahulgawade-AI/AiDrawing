"""
SQLAlchemy ORM model for Rule.
"""

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String

from townplanning.infrastructure.database.base import Base


class RuleModel(Base):

    __tablename__ = "rules"

    id = Column(
        String,
        primary_key=True,
    )

    regulation_id = Column(
        String,
        nullable=False,
        index=True,
    )

    category = Column(
        String,
        nullable=False,
    )

    name = Column(
        String,
        nullable=False,
    )

    description = Column(
        String,
        nullable=False,
    )

    condition_json = Column(
        JSON,
        default=dict,
        nullable=False,
    )

    result_json = Column(
        JSON,
        default=dict,
        nullable=False,
    )

    priority = Column(
        Integer,
        default=1,
        nullable=False,
    )

    enabled = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    metadata_json = Column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )