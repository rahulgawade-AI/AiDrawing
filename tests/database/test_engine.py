from sqlalchemy import text

from townplanning.infrastructure.database import (
    engine,
)


def test_engine():

    with engine.connect() as conn:

        result = conn.execute(
            text("SELECT 1")
        )

        assert result.scalar() == 1