"""
Tests database bootstrap.

Verifies that all registered SQLAlchemy models
create their corresponding database tables.
"""

from sqlalchemy import inspect

from townplanning.infrastructure.database.engine import engine


def test_database_tables_exist():

    inspector = inspect(engine)

    tables = inspector.get_table_names()

    expected_tables = {

        "regulations",

        "knowledge_cards",

    }

    for table in expected_tables:

        assert table in tables