from sqlalchemy import text

from townplanning.infrastructure.database import (
    SessionLocal,
)


def test_transaction():

    session = SessionLocal()

    try:

        session.execute(text("BEGIN"))

        session.execute(text("SELECT 1"))

        session.execute(text("ROLLBACK"))

    finally:

        session.close()