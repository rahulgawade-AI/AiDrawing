#!/usr/bin/env python3

"""
UDCPR PostgreSQL TABLES REBUILD

Purpose
-------
Completely rebuild public.tables from the authoritative UDCPR source chunks.

IMPORTANT
---------
- PostgreSQL only.
- regulations table is NOT modified.
- Chroma is NOT modified.
- Existing public.tables is NEVER deleted.
- Existing public.tables is renamed to a timestamped backup.
- A completely new public.tables is created.
- New tables are populated ONLY from:
      data/regulations/udcpr_canonical_manifest.json
      data/regulations/udcpr_source_chunks.json
- One PostgreSQL transaction is used for the actual rebuild.
- --dry-run is the default.
- --apply performs the actual rebuild.

EXPECTED SOURCE
---------------
Manifest regulations : 329
Source chunks        : 329
Source tables        : 1087

REBUILD FLOW
------------
1. Load manifest.
2. Load source chunks.
3. Validate manifest/chunk counts.
4. Resolve every source chunk to exactly one PostgreSQL regulation.
5. In --dry-run:
      perform NO database modification.
6. In --apply:
      create a PostgreSQL transaction
      lock tables
      rename existing public.tables -> backup
      create new public.tables
      insert all source tables
      verify everything
      COMMIT
7. If anything fails:
      ROLLBACK
      restore original public.tables name where possible.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.infrastructure.database.models import RegulationModel


# ============================================================
# CONSTANTS
# ============================================================

EXPECTED_REGULATIONS = 329
EXPECTED_CHUNKS = 329
EXPECTED_SOURCE_TABLES = 1087


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_space(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def normalize_number(value: Any) -> str:
    value = normalize_space(value)

    if not value:
        return ""

    value = value.replace(" ", "")

    value = re.sub(
        r"\s*\(\s*([a-z])\s*\)",
        r"(\1)",
        value,
        flags=re.IGNORECASE,
    )

    return value.lower()


def normalize_title(value: Any) -> str:
    return normalize_space(value).lower()


def regulation_key(
    number: Any,
    title: Any,
) -> str:

    return (
        normalize_number(number)
        + "|"
        + normalize_title(title)
    )


def load_json(path: str) -> Any:

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


# ============================================================
# SOURCE LOADERS
# ============================================================

def load_manifest(path: str) -> list[dict]:

    data = load_json(path)

    if isinstance(data, dict):

        entries = (
            data.get("regulations")
            or data.get("entries")
            or data.get("items")
            or []
        )

    elif isinstance(data, list):

        entries = data

    else:

        raise RuntimeError(
            "Manifest must be a JSON object or array."
        )

    if not isinstance(entries, list):

        raise RuntimeError(
            "Manifest regulations/entries is not a list."
        )

    return entries


def load_chunks(path: str) -> list[dict]:

    data = load_json(path)

    if isinstance(data, dict):

        chunks = (
            data.get("chunks")
            or data.get("source_chunks")
            or data.get("items")
            or []
        )

    elif isinstance(data, list):

        chunks = data

    else:

        raise RuntimeError(
            "Chunks must be a JSON object or array."
        )

    if not isinstance(chunks, list):

        raise RuntimeError(
            "Chunks collection is not a list."
        )

    return chunks


# ============================================================
# SOURCE TABLE HELPERS
# ============================================================

def chunk_tables(
    chunk: dict,
) -> list[dict]:

    for field in (
        "tables",
        "source_tables",
    ):

        value = chunk.get(field)

        if isinstance(value, list):
            return value

    return []


def source_table_id(
    table: dict,
) -> str:

    for field in (
        "table_id",
        "id",
    ):

        value = table.get(field)

        if value is not None:
            return str(value)

    raise RuntimeError(
        "Source table has no table_id/id."
    )


def source_table_page(
    table: dict,
) -> int:

    for field in (
        "pdf_page",
        "page_number",
        "page",
    ):

        value = table.get(field)

        if value is not None:

            try:
                return int(value)
            except (
                TypeError,
                ValueError,
            ):
                pass

    raise RuntimeError(
        "Source table has no valid page number."
    )


def source_table_index(
    table: dict,
) -> int:

    for field in (
        "table_index",
        "index",
    ):

        value = table.get(field)

        if value is not None:

            try:
                return int(value)
            except (
                TypeError,
                ValueError,
            ):
                pass

    raise RuntimeError(
        "Source table has no valid table index."
    )


def source_table_title(
    table: dict,
) -> str:

    value = table.get(
        "title",
        "",
    )

    return (
        value
        if isinstance(value, str)
        else str(value or "")
    )


def source_table_markdown(
    table: dict,
) -> str:

    for field in (
        "markdown",
        "table_markdown",
    ):

        value = table.get(field)

        if isinstance(value, str):
            return value

    return ""


def source_table_headers(
    table: dict,
):

    value = table.get(
        "headers",
        [],
    )

    if value is None:
        return []

    return value


def source_table_rows(
    table: dict,
):

    value = table.get(
        "rows",
        [],
    )

    if value is None:
        return []

    return value


def source_table_metadata(
    table: dict,
):

    value = table.get(
        "metadata",
        {},
    )

    if value is None:
        return {}

    return value


# ============================================================
# CHUNK -> REGULATION KEY
# ============================================================

def chunk_number(
    chunk: dict,
) -> str:

    for field in (
        "number",
        "regulation_number",
    ):

        value = chunk.get(field)

        if value is not None:
            return str(value)

    return ""


def chunk_title(
    chunk: dict,
) -> str:

    for field in (
        "title",
        "regulation_title",
    ):

        value = chunk.get(field)

        if value is not None:
            return str(value)

    return ""


def chunk_key(
    chunk: dict,
) -> str:

    number = chunk_number(chunk)
    title = chunk_title(chunk)

    return regulation_key(
        number,
        title,
    )


# ============================================================
# DATABASE REGULATIONS
# ============================================================

def load_database_regulations(
    db,
):

    rows = (
        db.query(
            RegulationModel
        )
        .order_by(
            RegulationModel.id
        )
        .all()
    )

    return rows


def build_database_regulation_index(
    regulations,
):

    index = defaultdict(list)

    for regulation in regulations:

        key = regulation_key(
            regulation.number,
            regulation.title,
        )

        index[key].append(
            regulation
        )

    return index


# ============================================================
# RESOLVE SOURCE CHUNKS
# ============================================================

def resolve_chunks(
    manifest,
    chunks,
    db_regulations,
):

    manifest_by_key = {}

    duplicate_manifest_keys = []

    for entry in manifest:

        number = entry.get(
            "number",
            "",
        )

        title = entry.get(
            "title",
            "",
        )

        key = regulation_key(
            number,
            title,
        )

        if not key:

            raise RuntimeError(
                "Manifest contains regulation "
                "without number/title."
            )

        if key in manifest_by_key:

            duplicate_manifest_keys.append(
                key
            )

        manifest_by_key[key] = entry

    if duplicate_manifest_keys:

        raise RuntimeError(
            "Duplicate manifest regulation keys: "
            + repr(
                duplicate_manifest_keys[:20]
            )
        )

    chunks_by_key = {}

    duplicate_chunk_keys = []

    for chunk in chunks:

        key = chunk_key(chunk)

        if not key:

            raise RuntimeError(
                "Source chunk has no number/title."
            )

        if key in chunks_by_key:

            duplicate_chunk_keys.append(
                key
            )

        chunks_by_key[key] = chunk

    if duplicate_chunk_keys:

        raise RuntimeError(
            "Duplicate source chunk keys: "
            + repr(
                duplicate_chunk_keys[:20]
            )
        )

    db_index = build_database_regulation_index(
        db_regulations
    )

    selected = {}

    missing = []

    ambiguous = []

    for key, entry in manifest_by_key.items():

        candidates = db_index.get(
            key,
            [],
        )

        if len(candidates) == 0:

            missing.append(
                {
                    "number":
                        entry.get("number"),
                    "title":
                        entry.get("title"),
                    "key":
                        key,
                }
            )

            continue

        if len(candidates) > 1:

            ambiguous.append(
                {
                    "number":
                        entry.get("number"),
                    "title":
                        entry.get("title"),
                    "key":
                        key,
                    "ids":
                        [
                            str(r.id)
                            for r in candidates
                        ],
                }
            )

            continue

        selected[key] = candidates[0]

    return (
        manifest_by_key,
        chunks_by_key,
        selected,
        missing,
        ambiguous,
    )


# ============================================================
# SOURCE TABLE COLLECTION
# ============================================================

def collect_source_tables(
    manifest_by_key,
    chunks_by_key,
    selected,
):

    records = []

    failures = []

    for key, entry in manifest_by_key.items():

        regulation = selected.get(key)

        if regulation is None:

            failures.append(
                {
                    "key": key,
                    "reason":
                        "No selected regulation.",
                }
            )

            continue

        chunk = chunks_by_key.get(key)

        if chunk is None:

            failures.append(
                {
                    "key": key,
                    "number":
                        entry.get("number"),
                    "title":
                        entry.get("title"),
                    "reason":
                        "Source chunk missing.",
                }
            )

            continue

        tables = chunk_tables(chunk)

        for table_position, table in enumerate(
            tables,
            start=1,
        ):

            try:

                record = {
                    "id":
                        source_table_id(table),

                    "regulation_id":
                        str(regulation.id),

                    "page_number":
                        source_table_page(table),

                    "table_index":
                        source_table_index(table),

                    "title":
                        source_table_title(table),

                    "headers":
                        source_table_headers(table),

                    "rows":
                        source_table_rows(table),

                    "markdown":
                        source_table_markdown(table),

                    "metadata":
                        source_table_metadata(table),
                }

                records.append(record)

            except Exception as exc:

                failures.append(
                    {
                        "key": key,
                        "number":
                            entry.get("number"),
                        "title":
                            entry.get("title"),
                        "table_position":
                            table_position,
                        "reason":
                            str(exc),
                    }
                )

    return records, failures


# ============================================================
# VALIDATE SOURCE
# ============================================================

def validate_source(
    manifest,
    chunks,
    source_tables,
):

    errors = []

    if len(manifest) != EXPECTED_REGULATIONS:

        errors.append(
            "Manifest regulation count is "
            f"{len(manifest)}, expected "
            f"{EXPECTED_REGULATIONS}."
        )

    if len(chunks) != EXPECTED_CHUNKS:

        errors.append(
            "Source chunk count is "
            f"{len(chunks)}, expected "
            f"{EXPECTED_CHUNKS}."
        )

    if len(source_tables) != EXPECTED_SOURCE_TABLES:

        errors.append(
            "Source table count is "
            f"{len(source_tables)}, expected "
            f"{EXPECTED_SOURCE_TABLES}."
        )

    ids = set()

    duplicate_ids = []

    for table in source_tables:

        table_id = table["id"]

        if table_id in ids:

            duplicate_ids.append(
                table_id
            )

        ids.add(table_id)

    if duplicate_ids:

        errors.append(
            "Duplicate source table IDs: "
            + repr(
                duplicate_ids[:20]
            )
        )

    invalid_page_index = []

    for table in source_tables:

        if table["page_number"] <= 0:

            invalid_page_index.append(
                {
                    "id":
                        table["id"],
                    "page":
                        table["page_number"],
                    "index":
                        table["table_index"],
                }
            )

        if table["table_index"] <= 0:

            invalid_page_index.append(
                {
                    "id":
                        table["id"],
                    "page":
                        table["page_number"],
                    "index":
                        table["table_index"],
                }
            )

    if invalid_page_index:

        errors.append(
            "Invalid source page/index values: "
            + repr(
                invalid_page_index[:20]
            )
        )

    duplicate_positions = []

    seen_positions = set()

    for table in source_tables:

        position = (
            table["regulation_id"],
            table["page_number"],
            table["table_index"],
        )

        if position in seen_positions:

            duplicate_positions.append(
                {
                    "regulation_id":
                        table["regulation_id"],
                    "page":
                        table["page_number"],
                    "index":
                        table["table_index"],
                    "table_id":
                        table["id"],
                }
            )

        seen_positions.add(position)

    if duplicate_positions:

        errors.append(
            "Duplicate "
            "(regulation_id,page_number,table_index) "
            "positions: "
            + repr(
                duplicate_positions[:20]
            )
        )

    return errors


# ============================================================
# SQL IDENTIFIER SAFETY
# ============================================================

def quote_identifier(
    name: str,
) -> str:

    return '"' + name.replace(
        '"',
        '""',
    ) + '"'


# ============================================================
# CREATE TABLE
# ============================================================

def create_tables_table(
    db,
):

    db.execute(
        text(
            """
            CREATE TABLE public."tables" (
                id TEXT PRIMARY KEY,

                regulation_id TEXT NOT NULL,

                page_number INTEGER NOT NULL,

                table_index INTEGER NOT NULL,

                title TEXT DEFAULT '',

                headers JSONB DEFAULT '[]'::jsonb,

                rows JSONB DEFAULT '[]'::jsonb,

                markdown TEXT DEFAULT '',

                metadata JSONB DEFAULT '{}'::jsonb,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT tables_regulation_id_fkey
                    FOREIGN KEY (regulation_id)
                    REFERENCES public.regulations(id)
                    ON DELETE CASCADE
            )
            """
        )
    )

    db.execute(
        text(
            """
            CREATE INDEX ix_tables_regulation_id
            ON public."tables" (regulation_id)
            """
        )
    )

    db.execute(
        text(
            """
            CREATE INDEX ix_tables_page_number
            ON public."tables" (page_number)
            """
        )
    )

    db.execute(
        text(
            """
            CREATE UNIQUE INDEX
                ux_tables_regulation_page_index
            ON public."tables"
                (regulation_id, page_number, table_index)
            """
        )
    )


# ============================================================
# INSERT
# ============================================================

INSERT_SQL = text(
    """
    INSERT INTO public."tables"
    (
        id,
        regulation_id,
        page_number,
        table_index,
        title,
        headers,
        rows,
        markdown,
        metadata
    )
    VALUES
    (
        :id,
        :regulation_id,
        :page_number,
        :table_index,
        :title,
        CAST(:headers AS JSONB),
        CAST(:rows AS JSONB),
        :markdown,
        CAST(:metadata AS JSONB)
    )
    """
)


def insert_source_tables(
    db,
    source_tables,
):

    inserted = 0

    for table in source_tables:

        db.execute(
            INSERT_SQL,
            {
                "id":
                    table["id"],

                "regulation_id":
                    table["regulation_id"],

                "page_number":
                    table["page_number"],

                "table_index":
                    table["table_index"],

                "title":
                    table["title"],

                "headers":
                    json.dumps(
                        table["headers"],
                        ensure_ascii=False,
                    ),

                "rows":
                    json.dumps(
                        table["rows"],
                        ensure_ascii=False,
                    ),

                "markdown":
                    table["markdown"],

                "metadata":
                    json.dumps(
                        table["metadata"],
                        ensure_ascii=False,
                    ),
            },
        )

        inserted += 1

    return inserted


# ============================================================
# BACKUP NAME
# ============================================================

def backup_table_name() -> str:

    return (
        "tables_backup_"
        + datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
    )


# ============================================================
# BACKUP EXISTING TABLE
# ============================================================

def rename_existing_tables(
    db,
    backup_name: str,
):

    exists = db.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'tables'
            )
            """
        )
    ).scalar_one()

    if not exists:

        raise RuntimeError(
            "public.tables does not exist."
        )

    db.execute(
        text(
            f"""
            ALTER TABLE public."tables"
            RENAME TO {quote_identifier(backup_name)}
            """
        )
    )


# ============================================================
# DATABASE VERIFICATION
# ============================================================

def verify_database(
    db,
    expected_count: int,
):

    failures = []

    source_count = expected_count

    database_count = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM public."tables"
            """
        )
    ).scalar_one()

    if database_count != source_count:

        failures.append(
            {
                "check":
                    "table_count",
                "expected":
                    source_count,
                "actual":
                    database_count,
            }
        )

    orphan_count = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM public."tables" t
            LEFT JOIN public.regulations r
              ON r.id = t.regulation_id
            WHERE r.id IS NULL
            """
        )
    ).scalar_one()

    if orphan_count != 0:

        failures.append(
            {
                "check":
                    "orphan_count",
                "expected":
                    0,
                "actual":
                    orphan_count,
            }
        )

    invalid_count = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM public."tables"
            WHERE page_number <= 0
               OR table_index <= 0
            """
        )
    ).scalar_one()

    if invalid_count != 0:

        failures.append(
            {
                "check":
                    "invalid_page_or_index",
                "expected":
                    0,
                "actual":
                    invalid_count,
            }
        )

    duplicate_position_count = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    regulation_id,
                    page_number,
                    table_index
                FROM public."tables"
                GROUP BY
                    regulation_id,
                    page_number,
                    table_index
                HAVING COUNT(*) > 1
            ) x
            """
        )
    ).scalar_one()

    if duplicate_position_count != 0:

        failures.append(
            {
                "check":
                    "duplicate_position_groups",
                "expected":
                    0,
                "actual":
                    duplicate_position_count,
            }
        )

    null_count = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM public."tables"
            WHERE id IS NULL
               OR regulation_id IS NULL
               OR page_number IS NULL
               OR table_index IS NULL
            """
        )
    ).scalar_one()

    if null_count != 0:

        failures.append(
            {
                "check":
                    "required_nulls",
                "expected":
                    0,
                "actual":
                    null_count,
            }
        )

    return {
        "source_table_count":
            source_count,

        "database_table_count":
            database_count,

        "orphan_count":
            orphan_count,

        "invalid_page_or_index_count":
            invalid_count,

        "duplicate_position_groups":
            duplicate_position_count,

        "required_null_count":
            null_count,

        "failures":
            failures,

        "passed":
            len(failures) == 0,
    }


# ============================================================
# REPORT
# ============================================================

def write_report(
    path: str,
    report: dict,
):

    Path(path).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
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


# ============================================================
# DRY RUN
# ============================================================

def dry_run(
    manifest_path: str,
    chunks_path: str,
    report_path: str,
):

    manifest = load_manifest(
        manifest_path
    )

    chunks = load_chunks(
        chunks_path
    )

    db = SessionLocal()

    try:

        db_regulations = load_database_regulations(
            db
        )

        (
            manifest_by_key,
            chunks_by_key,
            selected,
            missing,
            ambiguous,
        ) = resolve_chunks(
            manifest,
            chunks,
            db_regulations,
        )

        source_tables, source_failures = (
            collect_source_tables(
                manifest_by_key,
                chunks_by_key,
                selected,
            )
        )

        source_errors = validate_source(
            manifest,
            chunks,
            source_tables,
        )

        report = {
            "mode":
                "dry-run",

            "manifest":
                manifest_path,

            "chunks":
                chunks_path,

            "manifest_regulations":
                len(manifest),

            "source_chunks":
                len(chunks),

            "source_tables":
                len(source_tables),

            "selected_regulations":
                len(selected),

            "missing_regulations":
                missing,

            "ambiguous_regulations":
                ambiguous,

            "source_failures":
                source_failures,

            "source_errors":
                source_errors,

            "status":
                (
                    "READY FOR --apply"
                    if (
                        len(missing) == 0
                        and len(ambiguous) == 0
                        and len(source_failures) == 0
                        and len(source_errors) == 0
                    )
                    else
                    "NOT READY"
                ),
        }

        write_report(
            report_path,
            report,
        )

        print()
        print("=" * 120)
        print("UDCPR POSTGRESQL TABLE REBUILD")
        print("=" * 120)
        print()
        print("DRY-RUN MODE")
        print()
        print(
            "Manifest regulations:",
            len(manifest),
        )

        print(
            "Source chunks:",
            len(chunks),
        )

        print(
            "Source tables:",
            len(source_tables),
        )

        print(
            "Selected regulations:",
            len(selected),
        )

        print(
            "Missing regulations:",
            len(missing),
        )

        print(
            "Ambiguous regulations:",
            len(ambiguous),
        )

        print()

        if source_failures:

            print(
                "SOURCE FAILURES:",
                len(source_failures),
            )

            for failure in source_failures[:20]:

                print(
                    failure
                )

        if source_errors:

            print(
                "SOURCE ERRORS:"
            )

            for error in source_errors:

                print(
                    error
                )

        print()
        print("=" * 120)

        if report["status"] == "READY FOR --apply":

            print(
                "DRY-RUN COMPLETE"
            )

            print(
                "STATUS: READY FOR --apply"
            )

        else:

            print(
                "DRY-RUN FAILED"
            )

            print(
                "STATUS: NOT READY"
            )

        print(
            "Report:",
            report_path,
        )

        return (
            report["status"]
            == "READY FOR --apply"
        )

    finally:

        db.close()


# ============================================================
# APPLY
# ============================================================

def apply_rebuild(
    manifest_path: str,
    chunks_path: str,
    report_path: str,
):

    manifest = load_manifest(
        manifest_path
    )

    chunks = load_chunks(
        chunks_path
    )

    db = SessionLocal()

    backup_name = None

    report = {
        "mode":
            "apply",

        "manifest":
            manifest_path,

        "chunks":
            chunks_path,
    }

    try:

        db_regulations = load_database_regulations(
            db
        )

        (
            manifest_by_key,
            chunks_by_key,
            selected,
            missing,
            ambiguous,
        ) = resolve_chunks(
            manifest,
            chunks,
            db_regulations,
        )

        source_tables, source_failures = (
            collect_source_tables(
                manifest_by_key,
                chunks_by_key,
                selected,
            )
        )

        source_errors = validate_source(
            manifest,
            chunks,
            source_tables,
        )

        report.update(
            {
                "manifest_regulations":
                    len(manifest),

                "source_chunks":
                    len(chunks),

                "source_tables":
                    len(source_tables),

                "selected_regulations":
                    len(selected),

                "missing_regulations":
                    missing,

                "ambiguous_regulations":
                    ambiguous,

                "source_failures":
                    source_failures,

                "source_errors":
                    source_errors,
            }
        )

        if missing:

            raise RuntimeError(
                "Missing regulations detected."
            )

        if ambiguous:

            raise RuntimeError(
                "Ambiguous regulations detected."
            )

        if source_failures:

            raise RuntimeError(
                "Source table extraction failures detected."
            )

        if source_errors:

            raise RuntimeError(
                "Source validation failed:\n"
                + "\n".join(source_errors)
            )

        if len(source_tables) != EXPECTED_SOURCE_TABLES:

            raise RuntimeError(
                "Refusing rebuild because source table "
                f"count is {len(source_tables)}, "
                f"expected {EXPECTED_SOURCE_TABLES}."
            )

        print()
        print("=" * 120)
        print("UDCPR POSTGRESQL TABLE REBUILD")
        print("=" * 120)
        print()
        print("!!! APPLY MODE !!!")
        print()
        print(
            "Existing public.tables will be renamed "
            "to a timestamped backup."
        )

        print(
            "A completely new public.tables will "
            "be created."
        )

        print(
            "regulations will NOT be modified."
        )

        print()
        print(
            "Manifest:",
            manifest_path,
        )

        print(
            "Chunks:",
            chunks_path,
        )

        print(
            "Source tables:",
            len(source_tables),
        )

        print()

        # ----------------------------------------------------
        # START TRANSACTION
        # ----------------------------------------------------

        # Explicit transaction through SQLAlchemy session.
        # Nothing is committed until every verification passes.

        backup_name = backup_table_name()

        # Make sure generated backup name doesn't exist.
        existing_backup = db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = :name
                )
                """
            ),
            {
                "name":
                    backup_name
            },
        ).scalar_one()

        if existing_backup:

            raise RuntimeError(
                "Generated backup table already exists: "
                + backup_name
            )

        # ----------------------------------------------------
        # Lock regulations first.
        #
        # This prevents concurrent changes to the
        # regulation set while rebuilding tables.
        # ----------------------------------------------------

        db.execute(
            text(
                """
                LOCK TABLE public.regulations
                IN SHARE MODE
                """
            )
        )

        # ----------------------------------------------------
        # Backup existing tables
        # ----------------------------------------------------

        rename_existing_tables(
            db,
            backup_name,
        )

        # ----------------------------------------------------
        # Create clean tables table
        # ----------------------------------------------------

        create_tables_table(
            db
        )

        # ----------------------------------------------------
        # Insert authoritative source tables
        # ----------------------------------------------------

        inserted = insert_source_tables(
            db,
            source_tables,
        )

        if inserted != len(source_tables):

            raise RuntimeError(
                "Inserted count does not equal "
                "source count."
            )

        # ----------------------------------------------------
        # Verify inside SAME transaction
        # ----------------------------------------------------

        verification = verify_database(
            db,
            len(source_tables),
        )

        report.update(
            {
                "backup_table":
                    backup_name,

                "inserted_tables":
                    inserted,

                "verification":
                    verification,
            }
        )

        if not verification["passed"]:

            raise RuntimeError(
                "Database verification failed: "
                + json.dumps(
                    verification,
                    indent=2,
                )
            )

        # ----------------------------------------------------
        # COMMIT
        # ----------------------------------------------------

        db.commit()

        report["status"] = "SUCCESSFUL"

        write_report(
            report_path,
            report,
        )

        print()
        print("=" * 120)
        print("REBUILD SUCCESSFUL")
        print("=" * 120)

        print(
            "Backup table:",
            backup_name,
        )

        print(
            "Inserted tables:",
            inserted,
        )

        print(
            "Verification:",
            verification,
        )

        print()
        print(
            "PostgreSQL transaction COMMITTED."
        )

        print(
            "Old tables data remains in:",
            backup_name,
        )

        print(
            "Report:",
            report_path,
        )

        return 0

    except Exception as exc:

        # ----------------------------------------------------
        # ROLLBACK
        # ----------------------------------------------------

        try:

            db.rollback()

        except Exception:
            pass

        report["status"] = "ABORTED"

        report["error"] = str(exc)

        write_report(
            report_path,
            report,
        )

        print()
        print("=" * 120)
        print("REBUILD ABORTED")
        print("=" * 120)

        print(
            "NO COMMITTED DATABASE CHANGES."
        )

        print(
            "Report:",
            report_path,
        )

        print(
            "ERROR:",
            str(exc),
        )

        print()

        return 1

    finally:

        db.close()


# ============================================================
# ARGUMENTS
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Rebuild PostgreSQL public.tables "
            "from UDCPR source chunks."
        )
    )

    parser.add_argument(
        "--manifest",
        required=True,
    )

    parser.add_argument(
        "--chunks",
        required=True,
    )

    parser.add_argument(
        "--report",
        required=True,
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Actually rebuild PostgreSQL. "
            "Without --apply this is dry-run."
        ),
    )

    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_args()

    if not args.apply:

        ok = dry_run(
            args.manifest,
            args.chunks,
            args.report,
        )

        sys.exit(
            0 if ok else 1
        )

    sys.exit(
        apply_rebuild(
            args.manifest,
            args.chunks,
            args.report,
        )
    )


if __name__ == "__main__":

    main()
