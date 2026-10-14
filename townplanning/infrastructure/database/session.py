"""
Database Session.
"""

from sqlalchemy.orm import sessionmaker

from townplanning.infrastructure.database.engine import (
    engine,
)

SessionLocal = sessionmaker(

    bind=engine,

    autoflush=False,

    autocommit=False,

    expire_on_commit=False,
)