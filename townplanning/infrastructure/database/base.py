"""
SQLAlchemy Declarative Base.

Every ORM model in the project should inherit from Base.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass