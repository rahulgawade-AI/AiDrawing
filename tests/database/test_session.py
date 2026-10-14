from sqlalchemy import text

from townplanning.infrastructure.database import (
    SessionLocal,
)


def test_session():

    session = SessionLocal()

    try:

        value = session.execute(
            text("SELECT current_database()")
        ).scalar()

        assert value == "townplanning"

    finally:

        session.close()