"""
Creates all database tables.

Development only.

Alembic will replace this after schema freeze.
"""

from townplanning.infrastructure.database.base import Base

# IMPORTANT:
# Import models so they register with Base.metadata

import townplanning.infrastructure.database.models  # noqa

from townplanning.infrastructure.database.engine import (
    engine,
)


def main():

    print()

    print("=" * 60)

    print("Creating database schema...")

    print("=" * 60)

    Base.metadata.create_all(engine)

    print()

    print("Database initialized successfully.")

    print()


if __name__ == "__main__":

    main()