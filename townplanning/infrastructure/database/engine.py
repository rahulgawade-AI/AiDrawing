"""
Database Engine.
"""

from sqlalchemy import create_engine

from townplanning.core.settings import get_settings


settings = get_settings()

engine = create_engine(

    settings.DATABASE_URL,

    echo=False,

    future=True,
)