from __future__ import annotations

import json

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.infrastructure.database.repositories import (
    SQLAlchemyTableRepository,
)


KEYWORDS = [
    "setback",
    "margin",
    "marginal",
    "open space",
    "ground coverage",
    "coverage",
    "height",
    "storey",
    "floor",
    "parking",
    "tdr",
    "incentive",
    "fsi",
]


def main():

    session = SessionLocal()

    try:

        repo = SQLAlchemyTableRepository(session)

        print("=" * 120)
        print("PERSISTED UDCPR CONSTRAINT TABLES")
        print("=" * 120)

        tables = sorted(
            repo.list(),
            key=lambda x: (
                getattr(x, "page", 0) or 0,
                getattr(x, "index", 0) or 0,
            ),
        )

        for table in tables:

            title = (
                getattr(table, "title", "")
                or ""
            )

            headers = (
                getattr(table, "headers", [])
                or []
            )

            rows = (
                getattr(table, "rows", [])
                or []
            )

            text = " ".join(
                [
                    str(title),
                    *[
                        str(x)
                        for x in headers
                    ],
                    *[
                        str(x)
                        for row in rows
                        for x in (
                            row
                            if isinstance(row, list)
                            else [row]
                        )
                    ],
                ]
            ).lower()

            matched = [
                keyword
                for keyword in KEYWORDS
                if keyword in text
            ]

            if not matched:
                continue

            print()
            print("=" * 120)

            print(
                "PAGE       :",
                getattr(table, "page", None),
            )

            print(
                "INDEX      :",
                getattr(table, "index", None),
            )

            print(
                "TITLE      :",
                repr(title),
            )

            print(
                "MATCHED    :",
                ", ".join(matched),
            )

            print()
            print("HEADERS:")
            print(
                json.dumps(
                    headers,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            print()
            print("ROWS:")
            print(
                json.dumps(
                    rows,
                    indent=2,
                    ensure_ascii=False,
                )
            )

        print()
        print("=" * 120)
        print("END")
        print("=" * 120)

    finally:
        session.close()


if __name__ == "__main__":
    main()
