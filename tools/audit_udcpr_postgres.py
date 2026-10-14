#!/usr/bin/env python3

"""
READ-ONLY UDCPR PostgreSQL AUDIT

Purpose
-------
Audit the existing PostgreSQL UDCPR data before any destructive rebuild.

This script DOES NOT:
    - INSERT
    - UPDATE
    - DELETE
    - COMMIT changes
    - modify Chroma

It compares:
    1. Existing PostgreSQL regulations
    2. Canonical 329-entry UDCPR manifest
    3. Existing tables and their regulation_id
    4. Existing rules / knowledge_cards where available

The audit is intentionally conservative.
It does NOT assume that existing table.regulation_id is correct.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.infrastructure.database.models import RegulationModel


DEFAULT_MANIFEST = (
    "data/regulations/udcpr_canonical_manifest.json"
)

DEFAULT_REPORT = (
    "/tmp/udcpr_postgres_audit.json"
)


# ============================================================
# HELPERS
# ============================================================

def clean(value: Any) -> str:
    if value is None:
        return ""

    value = str(value)

    value = value.replace("\u00a0", " ")
    value = value.replace("\r", "\n")

    value = re.sub(
        r"[ \t]+",
        " ",
        value,
    )

    value = re.sub(
        r"\n{3,}",
        "\n\n",
        value,
    )

    return value.strip()


def normalize_number(value: Any) -> str:
    value = clean(value)

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    value = re.sub(
        r"\s*\(\s*",
        "(",
        value,
    )

    value = re.sub(
        r"\s*\)\s*",
        ")",
        value,
    )

    return value


def normalize_title(value: Any) -> str:
    value = clean(value).lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def is_canonical_number(number: str) -> bool:
    """
    Canonical UDCPR regulation numbers look like:

        1.0
        1.1
        2.2
        2.2.1
        2.2.5(a)
        14.1.1.6(i)

    This does NOT mean every syntactically valid number
    is actually canonical. The manifest decides that.
    """

    return bool(
        re.fullmatch(
            r"\d+(?:\.\d+)*(?:\([A-Za-z]+\))?",
            number,
        )
    )


def is_fragment_number(number: str) -> bool:
    """
    Detect numbers that are almost certainly extracted
    sub-items rather than canonical regulations.

    Examples:
        (c)
        (i)
        (iii)
        (1)
        (v)(a)
        1)
        3
        (#) 3
    """

    n = clean(number)

    if re.fullmatch(
        r"\(?[a-zivxlcdm]+\)?(?:\([a-zivxlcdm]+\))*",
        n,
        re.IGNORECASE,
    ):
        return True

    if re.fullmatch(
        r"\(?\d+\)?[.)]?",
        n,
    ):
        return True

    if re.search(
        r"[\*\#]",
        n,
    ):
        return True

    return False


def canonical_key(
    number: str,
    title: str,
) -> tuple[str, str]:

    return (
        normalize_number(number),
        normalize_title(title),
    )


# ============================================================
# MANIFEST
# ============================================================

def load_manifest(path: Path) -> list[dict[str, Any]]:

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    entries = data.get(
        "regulations",
        data.get(
            "entries",
            [],
        ),
    )

    if not isinstance(
        entries,
        list,
    ):
        raise RuntimeError(
            "Manifest does not contain "
            "'regulations' or 'entries'."
        )

    return entries


# ============================================================
# SCHEMA AUDIT
# ============================================================

def inspect_schema(db) -> dict[str, Any]:

    inspector = inspect(
        db.bind
    )

    tables = inspector.get_table_names()

    result = {
        "database_tables": sorted(
            tables
        ),
        "table_columns": {},
        "foreign_keys": {},
    }

    interesting = [
        "regulations",
        "tables",
        "rules",
        "knowledge_cards",
        "ocr_documents",
        "ocr_regulation_links",
    ]

    for table_name in interesting:

        if table_name not in tables:
            continue

        columns = inspector.get_columns(
            table_name
        )

        result[
            "table_columns"
        ][table_name] = [
            {
                "name": c["name"],
                "type": str(c["type"]),
                "nullable": c.get(
                    "nullable"
                ),
            }
            for c in columns
        ]

        result[
            "foreign_keys"
        ][table_name] = (
            inspector.get_foreign_keys(
                table_name
            )
        )

    return result


# ============================================================
# REGULATION AUDIT
# ============================================================

def audit_regulations(
    db,
    manifest_entries,
) -> dict[str, Any]:

    rows = (
        db.query(
            RegulationModel
        )
        .order_by(
            RegulationModel.number,
            RegulationModel.page_start,
        )
        .all()
    )

    canonical = {}

    for entry in manifest_entries:

        number = normalize_number(
            entry.get("number")
        )

        title = normalize_title(
            entry.get("title")
        )

        key = (
            number,
            title,
        )

        canonical[key] = {
            "number": number,
            "title": entry.get("title", ""),
            "printed_page_start": entry.get(
                "printed_page_start"
            ),
            "printed_page_end": entry.get(
                "printed_page_end"
            ),
            "chapter": entry.get(
                "chapter"
            ),
            "variant": entry.get(
                "variant"
            ),
        }

    existing_by_key = defaultdict(list)
    existing_by_number = defaultdict(list)

    existing_rows = []

    for row in rows:

        number = normalize_number(
            row.number
        )

        title = clean(
            row.title
        )

        key = canonical_key(
            number,
            title,
        )

        item = {
            "id": str(row.id),
            "number": row.number,
            "normalized_number": number,
            "chapter": row.chapter,
            "title": title,
            "page_start": row.page_start,
            "page_end": row.page_end,
            "text_length": len(
                row.text or ""
            ),
            "canonical_key": key,
            "is_fragment_number":
                is_fragment_number(number),
            "is_syntactically_canonical":
                is_canonical_number(number),
        }

        existing_rows.append(
            item
        )

        existing_by_key[key].append(
            item
        )

        existing_by_number[
            number
        ].append(item)

    exact_matches = []
    unmatched_existing = []
    missing_canonical = []

    for key, items in existing_by_key.items():

        if key in canonical:

            for item in items:
                exact_matches.append(
                    item
                )

        else:

            for item in items:
                unmatched_existing.append(
                    item
                )

    for key, entry in canonical.items():

        if key not in existing_by_key:
            missing_canonical.append(
                entry
            )

    duplicate_numbers = []

    for number, items in existing_by_number.items():

        if len(items) > 1:

            duplicate_numbers.append(
                {
                    "number": number,
                    "count": len(items),
                    "rows": items,
                }
            )

    duplicate_exact_records = []

    for key, items in existing_by_key.items():

        if len(items) > 1:

            duplicate_exact_records.append(
                {
                    "number": key[0],
                    "title": key[1],
                    "count": len(items),
                    "rows": items,
                }
            )

    fragment_rows = [
        x
        for x in existing_rows
        if x["is_fragment_number"]
    ]

    empty_text = [
        x
        for x in existing_rows
        if x["text_length"] == 0
    ]

    page_anomalies = []

    for x in existing_rows:

        start = x["page_start"]
        end = x["page_end"]

        if (
            start is not None
            and end is not None
            and end < start
        ):
            page_anomalies.append(
                x
            )

    canonical_existing = [
        x
        for x in existing_rows
        if x["canonical_key"]
        in canonical
    ]

    return {
        "existing_count": len(rows),
        "canonical_count": len(canonical),
        "exact_canonical_matches":
            len(canonical_existing),
        "missing_canonical_count":
            len(missing_canonical),
        "unmatched_existing_count":
            len(unmatched_existing),
        "duplicate_number_count":
            len(duplicate_numbers),
        "duplicate_exact_record_count":
            len(duplicate_exact_records),
        "fragment_regulation_count":
            len(fragment_rows),
        "empty_text_count":
            len(empty_text),
        "page_anomaly_count":
            len(page_anomalies),

        "duplicate_numbers":
            duplicate_numbers,

        "duplicate_exact_records":
            duplicate_exact_records,

        "fragment_rows":
            fragment_rows,

        "empty_text_rows":
            empty_text,

        "page_anomalies":
            page_anomalies,

        "missing_canonical":
            missing_canonical,

        "unmatched_existing":
            unmatched_existing,

        "canonical_matches":
            canonical_existing,
    }


# ============================================================
# TABLE AUDIT
# ============================================================

def table_columns(
    db,
    table_name: str,
) -> list[str]:

    inspector = inspect(
        db.bind
    )

    if table_name not in inspector.get_table_names():
        return []

    return [
        c["name"]
        for c in inspector.get_columns(
            table_name
        )
    ]


def audit_tables(
    db,
    canonical_entries,
) -> dict[str, Any]:

    inspector = inspect(
        db.bind
    )

    db_tables = inspector.get_table_names()

    if "tables" not in db_tables:

        return {
            "table_exists": False,
            "reason":
                "PostgreSQL table named 'tables' "
                "was not found.",
        }

    cols = table_columns(
        db,
        "tables",
    )

    required = {
        "id",
        "regulation_id",
    }

    missing_columns = sorted(
        required - set(cols)
    )

    if missing_columns:

        return {
            "table_exists": True,
            "columns": cols,
            "missing_required_columns":
                missing_columns,
        }

    result = {
        "table_exists": True,
        "columns": cols,
        "total_tables": 0,
        "missing_regulation_id": 0,
        "unknown_regulation_id": 0,
        "tables_by_regulation": {},
        "table_samples": [],
    }

    rows = db.execute(
        text(
            "SELECT * FROM tables"
        )
    ).mappings().all()

    result[
        "total_tables"
    ] = len(rows)

    regulation_rows = db.execute(
        text(
            """
            SELECT
                id,
                number,
                title,
                page_start,
                page_end
            FROM regulations
            """
        )
    ).mappings().all()

    regulation_map = {
        str(x["id"]): x
        for x in regulation_rows
    }

    grouped = defaultdict(list)

    for row in rows:

        rid = row.get(
            "regulation_id"
        )

        if rid is None:

            result[
                "missing_regulation_id"
            ] += 1

            owner = "NULL"

        else:

            owner = str(rid)

            if owner not in regulation_map:

                result[
                    "unknown_regulation_id"
                ] += 1

        grouped[
            owner
        ].append(
            row
        )

    # --------------------------------------------------------
    # Existing table ownership
    # --------------------------------------------------------

    for rid, table_rows in grouped.items():

        regulation = regulation_map.get(
            rid
        )

        result[
            "tables_by_regulation"
        ][rid] = {
            "regulation": (
                dict(regulation)
                if regulation
                else None
            ),
            "table_count":
                len(table_rows),
            "tables": [
                {
                    key: value
                    for key, value in row.items()
                    if key in {
                        "id",
                        "regulation_id",
                        "page_number",
                        "table_index",
                        "title",
                        "headers",
                        "rows",
                        "markdown",
                        "metadata",
                    }
                }
                for row in table_rows
            ],
        }

    # --------------------------------------------------------
    # Samples
    # --------------------------------------------------------

    for row in rows[:100]:

        rid = row.get(
            "regulation_id"
        )

        owner = regulation_map.get(
            str(rid)
        ) if rid is not None else None

        result[
            "table_samples"
        ].append(
            {
                "table_id":
                    str(row.get("id")),
                "regulation_id":
                    str(rid)
                    if rid is not None
                    else None,
                "regulation_number":
                    owner["number"]
                    if owner
                    else None,
                "regulation_title":
                    owner["title"]
                    if owner
                    else None,
                "page_number":
                    row.get("page_number"),
                "table_index":
                    row.get("table_index"),
                "title":
                    row.get("title"),
                "markdown_preview":
                    clean(
                        row.get(
                            "markdown"
                        )
                    )[:500],
            }
        )

    return result


# ============================================================
# CHILD RECORD AUDIT
# ============================================================

def audit_child_table(
    db,
    table_name: str,
) -> dict[str, Any]:

    inspector = inspect(
        db.bind
    )

    if table_name not in inspector.get_table_names():

        return {
            "exists": False
        }

    columns = table_columns(
        db,
        table_name,
    )

    result = {
        "exists": True,
        "columns": columns,
    }

    if "regulation_id" not in columns:

        result[
            "regulation_id_column"
        ] = False

        return result

    rows = db.execute(
        text(
            f"""
            SELECT regulation_id
            FROM {table_name}
            """
        )
    ).scalars().all()

    result[
        "count"
    ] = len(rows)

    result[
        "null_regulation_id"
    ] = sum(
        x is None
        for x in rows
    )

    regulation_ids = {
        str(x.id)
        for x in db.query(
            RegulationModel.id
        ).all()
    }

    result[
        "unknown_regulation_id"
    ] = sum(
        x is not None
        and str(x) not in regulation_ids
        for x in rows
    )

    return result


# ============================================================
# CANONICAL NUMBER DISTRIBUTION
# ============================================================

def canonical_number_summary(
    manifest_entries,
) -> dict[str, Any]:

    numbers = [
        normalize_number(
            e.get("number")
        )
        for e in manifest_entries
    ]

    counts = Counter(
        numbers
    )

    return {
        "count": len(numbers),
        "unique_numbers":
            len(counts),
        "duplicate_numbers": {
            number: count
            for number, count
            in counts.items()
            if count > 1
        },
        "first_20":
            numbers[:20],
        "last_20":
            numbers[-20:],
    }


# ============================================================
# MAIN AUDIT
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit of existing "
            "UDCPR PostgreSQL data."
        )
    )

    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
    )

    parser.add_argument(
        "--report",
        default=DEFAULT_REPORT,
    )

    args = parser.parse_args()

    manifest_path = Path(
        args.manifest
    )

    report_path = Path(
        args.report
    )

    print()
    print("=" * 110)
    print(
        "UDCPR POSTGRESQL READ-ONLY AUDIT"
    )
    print("=" * 110)
    print(
        "Manifest:",
        manifest_path,
    )
    print(
        "Report  :",
        report_path,
    )
    print()
    print(
        "NO INSERT / UPDATE / DELETE WILL BE PERFORMED."
    )
    print("=" * 110)

    manifest_entries = load_manifest(
        manifest_path
    )

    db = SessionLocal()

    try:

        schema = inspect_schema(
            db
        )

        regulations = audit_regulations(
            db,
            manifest_entries,
        )

        tables = audit_tables(
            db,
            manifest_entries,
        )

        rules = audit_child_table(
            db,
            "rules",
        )

        cards = audit_child_table(
            db,
            "knowledge_cards",
        )

        ocr_links = audit_child_table(
            db,
            "ocr_regulation_links",
        )

        report = {
            "audit": {
                "timestamp":
                    datetime.utcnow().isoformat()
                    + "Z",
                "read_only": True,
                "manifest":
                    str(manifest_path),
            },

            "canonical_manifest": {
                "entry_count":
                    len(manifest_entries),
                "number_summary":
                    canonical_number_summary(
                        manifest_entries
                    ),
            },

            "schema": schema,

            "regulations": regulations,

            "tables": tables,

            "rules": rules,

            "knowledge_cards": cards,

            "ocr_regulation_links":
                ocr_links,
        }

        report_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with report_path.open(
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                report,
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        # ====================================================
        # CONSOLE SUMMARY
        # ====================================================

        print()
        print("=" * 110)
        print(
            "REGULATION SUMMARY"
        )
        print("=" * 110)

        print(
            "Canonical manifest :",
            regulations[
                "canonical_count"
            ],
        )

        print(
            "PostgreSQL rows    :",
            regulations[
                "existing_count"
            ],
        )

        print(
            "Canonical matches  :",
            regulations[
                "exact_canonical_matches"
            ],
        )

        print(
            "Missing canonical  :",
            regulations[
                "missing_canonical_count"
            ],
        )

        print(
            "Unmatched existing :",
            regulations[
                "unmatched_existing_count"
            ],
        )

        print(
            "Duplicate numbers  :",
            regulations[
                "duplicate_number_count"
            ],
        )

        print(
            "Duplicate exact    :",
            regulations[
                "duplicate_exact_record_count"
            ],
        )

        print(
            "Fragment rows      :",
            regulations[
                "fragment_regulation_count"
            ],
        )

        print(
            "Empty text         :",
            regulations[
                "empty_text_count"
            ],
        )

        print(
            "Page anomalies     :",
            regulations[
                "page_anomaly_count"
            ],
        )

        print()
        print("=" * 110)
        print(
            "TABLE SUMMARY"
        )
        print("=" * 110)

        if tables.get(
            "table_exists"
        ):

            print(
                "tables rows        :",
                tables.get(
                    "total_tables",
                    0,
                ),
            )

            print(
                "NULL regulation_id :",
                tables.get(
                    "missing_regulation_id",
                    0,
                ),
            )

            print(
                "Unknown reg ID     :",
                tables.get(
                    "unknown_regulation_id",
                    0,
                ),
            )

        else:

            print(
                "PostgreSQL 'tables' "
                "table NOT FOUND"
            )

        print()
        print("=" * 110)
        print(
            "CHILD RECORD SUMMARY"
        )
        print("=" * 110)

        for name, value in (
            (
                "rules",
                rules,
            ),
            (
                "knowledge_cards",
                cards,
            ),
            (
                "ocr_regulation_links",
                ocr_links,
            ),
        ):

            print(
                f"{name:24}:",
                value.get(
                    "count",
                    "N/A",
                ),
            )

            if value.get(
                "exists"
            ):

                print(
                    f"{'  NULL regulation_id':24}:",
                    value.get(
                        "null_regulation_id",
                        0,
                    ),
                )

                print(
                    f"{'  unknown regulation_id':24}:",
                    value.get(
                        "unknown_regulation_id",
                        0,
                    ),
                )

        # ====================================================
        # DUPLICATE NUMBERS
        # ====================================================

        print()
        print("=" * 110)
        print(
            "DUPLICATE REGULATION NUMBERS"
        )
        print("=" * 110)

        duplicates = regulations[
            "duplicate_numbers"
        ]

        if not duplicates:

            print(
                "NONE"
            )

        else:

            for item in duplicates:

                print(
                    item["number"],
                    "->",
                    item["count"],
                    "rows",
                )

                for row in item[
                    "rows"
                ]:

                    print(
                        "   ",
                        row["id"],
                        "|",
                        row["title"],
                        "| page",
                        row["page_start"],
                        "-",
                        row["page_end"],
                    )

        # ====================================================
        # FRAGMENTS
        # ====================================================

        print()
        print("=" * 110)
        print(
            "SUSPICIOUS FRAGMENT REGULATIONS"
        )
        print("=" * 110)

        fragments = regulations[
            "fragment_rows"
        ]

        print(
            "Count:",
            len(fragments),
        )

        for row in fragments[:100]:

            print(
                row["id"],
                "|",
                row["number"],
                "|",
                row["title"][:100],
                "| page",
                row["page_start"],
            )

        if len(fragments) > 100:

            print(
                "...",
                len(fragments) - 100,
                "more; see JSON report."
            )

        # ====================================================
        # MISSING CANONICAL
        # ====================================================

        print()
        print("=" * 110)
        print(
            "MISSING CANONICAL REGULATIONS"
        )
        print("=" * 110)

        missing = regulations[
            "missing_canonical"
        ]

        print(
            "Count:",
            len(missing),
        )

        for row in missing[:100]:

            print(
                row.get("number"),
                "|",
                row.get("title"),
                "| page",
                row.get(
                    "printed_page_start"
                ),
            )

        # ====================================================
        # TABLE OWNERSHIP DISTRIBUTION
        # ====================================================

        if tables.get(
            "table_exists"
        ):

            print()
            print("=" * 110)
            print(
                "TOP REGULATIONS BY CURRENT TABLE COUNT"
            )
            print("=" * 110)

            distribution = []

            for rid, value in tables.get(
                "tables_by_regulation",
                {},
            ).items():

                regulation = value.get(
                    "regulation"
                )

                distribution.append(
                    (
                        value[
                            "table_count"
                        ],
                        regulation,
                    )
                )

            distribution.sort(
                reverse=True,
                key=lambda x: x[0],
            )

            for count, regulation in distribution[:50]:

                if regulation:

                    print(
                        f"{regulation['number']:15}",
                        "|",
                        f"{count:4}",
                        "tables |",
                        regulation[
                            "title"
                        ][:100],
                    )

                else:

                    print(
                        "UNKNOWN",
                        "|",
                        count,
                        "tables",
                    )

        print()
        print("=" * 110)
        print(
            "AUDIT COMPLETE"
        )
        print("=" * 110)

        print(
            "JSON report:",
            report_path,
        )

        print()
        print(
            "IMPORTANT:"
        )
        print(
            "Existing tables.regulation_id mappings "
            "have NOT been assumed correct."
        )
        print(
            "This report is for mapping/rebuild analysis "
            "only. PostgreSQL was not modified."
        )

    finally:

        db.close()


if __name__ == "__main__":
    main()
