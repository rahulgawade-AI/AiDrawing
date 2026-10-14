#!/usr/bin/env python3

"""
UDCPR PDF <-> PostgreSQL TABLE VERIFICATION

READ-ONLY.

This script verifies the rebuilt PostgreSQL "tables" table against:

    1. Actual UDCPR PDF
    2. data/regulations/udcpr_source_chunks.json
    3. PostgreSQL regulations
    4. PostgreSQL tables

NO DATABASE CHANGES ARE MADE.

Checks:

    - PDF exists and can be opened
    - Source chunks count
    - Source table count
    - PostgreSQL table count
    - Every PostgreSQL table has a valid regulation
    - Every table has valid page_number/table_index
    - Source table -> PostgreSQL table mapping
    - Page number consistency
    - Table index consistency
    - Markdown/content hash consistency
    - Regulation number/title consistency
    - Special check for 5.12
    - Duplicate source table detection
    - Missing source tables
    - Extra PostgreSQL tables

The source_chunks JSON remains the authoritative extracted
representation of the PDF tables. The PDF itself is used to
verify that the referenced pages exist and that the source
document is readable.

Usage:

    python tools/verify_udcpr_pdf_postgres.py \
      --pdf /path/to/UDCPR.pdf \
      --chunks data/regulations/udcpr_source_chunks.json \
      --report /tmp/udcpr_pdf_postgres_verification.json

Example:

    python tools/verify_udcpr_pdf_postgres.py \
      --pdf data/regulations/UDCPR.pdf \
      --chunks data/regulations/udcpr_source_chunks.json \
      --report /tmp/udcpr_pdf_postgres_verification.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import text

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.infrastructure.database.models import RegulationModel


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_space(value):

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def normalize_number(value):

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

    return value


def normalize_title(value):

    return normalize_space(value).lower()


def normalize_text(value):

    if value is None:
        return ""

    return (
        str(value)
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
    )


def sha256_text(value):

    return hashlib.sha256(
        normalize_text(value).encode("utf-8")
    ).hexdigest()


def title_key(number, title):

    return (
        normalize_number(number)
        + "|"
        + normalize_title(title)
    )


# ============================================================
# TABLE NORMALIZATION
# ============================================================

def normalize_table_markdown(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace("\r\n", "\n")
    value = value.replace("\r", "\n")

    # Remove trailing spaces.
    value = "\n".join(
        line.rstrip()
        for line in value.split("\n")
    )

    # Normalize leading/trailing whitespace only.
    return value.strip()


def table_hash(value):

    return sha256_text(
        normalize_table_markdown(value)
    )


# ============================================================
# JSON LOAD
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


# ============================================================
# SOURCE CHUNKS
# ============================================================

def load_chunks(path):

    data = load_json(path)

    if isinstance(data, list):
        chunks = data

    elif isinstance(data, dict):

        chunks = (
            data.get("chunks")
            or data.get("source_chunks")
            or data.get("items")
            or []
        )

    else:

        raise RuntimeError(
            "Unsupported source chunks JSON format."
        )

    if not isinstance(chunks, list):

        raise RuntimeError(
            "Source chunks is not a list."
        )

    return chunks


def chunk_tables(chunk):

    for field in (
        "tables",
        "source_tables",
    ):

        value = chunk.get(field)

        if isinstance(value, list):

            return value

    return []


def source_table_markdown(table):

    for field in (
        "markdown",
        "table_markdown",
    ):

        value = table.get(field)

        if isinstance(value, str):

            return value

    return ""


def source_table_page(table):

    value = table.get(
        "pdf_page",
        table.get(
            "page_number"
        ),
    )

    try:

        return int(value)

    except (
        TypeError,
        ValueError,
    ):

        return None


def source_table_index(table):

    value = table.get(
        "table_index"
    )

    try:

        return int(value)

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# BUILD SOURCE TABLE INDEX
# ============================================================

def build_source_tables(chunks):

    result = []

    for chunk_number, chunk in enumerate(
        chunks,
        start=1,
    ):

        number = chunk.get(
            "number"
        )

        title = chunk.get(
            "title"
        )

        key = title_key(
            number,
            title,
        )

        for table_position, table in enumerate(
            chunk_tables(chunk),
            start=1,
        ):

            markdown = source_table_markdown(
                table
            )

            page = source_table_page(
                table
            )

            index = source_table_index(
                table
            )

            result.append(
                {
                    "source_id":
                        f"{chunk_number}:{table_position}",

                    "number":
                        number,

                    "title":
                        title,

                    "key":
                        key,

                    "pdf_page":
                        page,

                    "table_index":
                        index,

                    "markdown":
                        markdown,

                    "hash":
                        table_hash(markdown),
                }
            )

    return result


# ============================================================
# PDF CHECK
# ============================================================

def inspect_pdf(pdf_path):

    result = {
        "path":
            str(pdf_path),

        "exists":
            pdf_path.exists(),

        "size_bytes":
            0,

        "page_count":
            None,

        "error":
            None,
    }

    if not pdf_path.exists():

        result["error"] = (
            "PDF file does not exist."
        )

        return result

    result["size_bytes"] = (
        pdf_path.stat().st_size
    )

    try:

        from pypdf import PdfReader

        reader = PdfReader(
            str(pdf_path)
        )

        result["page_count"] = len(
            reader.pages
        )

    except Exception as exc:

        result["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    return result


# ============================================================
# DATABASE LOAD
# ============================================================

def load_database(db):

    regulations = (
        db.query(
            RegulationModel
        )
        .all()
    )

    regulation_by_id = {
        str(row.id):
            row
        for row in regulations
    }

    tables = db.execute(
        text(
            """
            SELECT
                id,
                regulation_id,
                page_number,
                table_index,
                title,
                headers,
                rows,
                markdown,
                metadata
            FROM "tables"
            ORDER BY
                page_number,
                table_index,
                id
            """
        )
    ).mappings().all()

    return (
        regulations,
        regulation_by_id,
        tables,
    )


# ============================================================
# DATABASE TABLE KEY
# ============================================================

def database_table_key(
    regulation_id,
    page,
    index,
    markdown,
):

    return (
        str(regulation_id),
        int(page),
        int(index),
        table_hash(markdown),
    )


# ============================================================
# VERIFY
# ============================================================

def verify(
    pdf_info,
    source_tables,
    regulations,
    regulation_by_id,
    db_tables,
):

    failures = []

    warnings = []

    # --------------------------------------------------------
    # Counts
    # --------------------------------------------------------

    source_count = len(
        source_tables
    )

    database_count = len(
        db_tables
    )

    # --------------------------------------------------------
    # PDF page validity
    # --------------------------------------------------------

    pdf_page_count = (
        pdf_info.get(
            "page_count"
        )
    )

    invalid_source_pdf_pages = []

    for source in source_tables:

        page = source["pdf_page"]

        if page is None:

            invalid_source_pdf_pages.append(
                {
                    "source_id":
                        source["source_id"],
                    "page":
                        page,
                }
            )

            continue

        if (
            pdf_page_count is not None
            and (
                page < 1
                or page > pdf_page_count
            )
        ):

            invalid_source_pdf_pages.append(
                {
                    "source_id":
                        source["source_id"],
                    "page":
                        page,
                    "pdf_page_count":
                        pdf_page_count,
                }
            )

    if invalid_source_pdf_pages:

        failures.append(
            {
                "type":
                    "invalid_source_pdf_page",
                "count":
                    len(
                        invalid_source_pdf_pages
                    ),
                "items":
                    invalid_source_pdf_pages[:100],
            }
        )

    # --------------------------------------------------------
    # PostgreSQL orphan check
    # --------------------------------------------------------

    orphan_tables = []

    for table in db_tables:

        rid = str(
            table["regulation_id"]
        )

        if rid not in regulation_by_id:

            orphan_tables.append(
                {
                    "table_id":
                        str(table["id"]),
                    "regulation_id":
                        rid,
                }
            )

    if orphan_tables:

        failures.append(
            {
                "type":
                    "orphan_table",
                "count":
                    len(
                        orphan_tables
                    ),
                "items":
                    orphan_tables[:100],
            }
        )

    # --------------------------------------------------------
    # Invalid database page/index
    # --------------------------------------------------------

    invalid_database_page_index = []

    for table in db_tables:

        page = table["page_number"]

        index = table["table_index"]

        if (
            page is None
            or page < 1
            or index is None
            or index < 1
        ):

            invalid_database_page_index.append(
                {
                    "table_id":
                        str(table["id"]),
                    "page":
                        page,
                    "index":
                        index,
                }
            )

    if invalid_database_page_index:

        failures.append(
            {
                "type":
                    "invalid_database_page_or_index",
                "count":
                    len(
                        invalid_database_page_index
                    ),
                "items":
                    invalid_database_page_index[:100],
            }
        )

    # --------------------------------------------------------
    # Build PostgreSQL lookup
    #
    # A regulation may have many tables.
    # --------------------------------------------------------

    db_by_reg_page_index = defaultdict(
        list
    )

    for table in db_tables:

        key = (
            str(table["regulation_id"]),
            table["page_number"],
            table["table_index"],
        )

        db_by_reg_page_index[
            key
        ].append(table)

    # --------------------------------------------------------
    # Source regulation -> selected DB regulation
    # --------------------------------------------------------

    source_regulations = {}

    for source in source_tables:

        source_regulations[
            source["key"]
        ] = source

    # --------------------------------------------------------
    # Match source tables
    #
    # First match by regulation key + page + index.
    #
    # Then compare markdown hash.
    # --------------------------------------------------------

    matched = 0

    missing = []

    content_mismatch = []

    ambiguous = []

    page_index_mismatch = []

    source_to_db = []

    # Build regulation candidates.
    regulations_by_key = defaultdict(
        list
    )

    for regulation in regulations:

        key = title_key(
            regulation.number,
            regulation.title,
        )

        regulations_by_key[
            key
        ].append(
            regulation
        )

    for source in source_tables:

        candidates = regulations_by_key.get(
            source["key"],
            [],
        )

        if len(candidates) != 1:

            ambiguous.append(
                {
                    "source_id":
                        source["source_id"],
                    "number":
                        source["number"],
                    "title":
                        source["title"],
                    "candidate_count":
                        len(candidates),
                    "candidate_ids":
                        [
                            str(x.id)
                            for x in candidates
                        ],
                }
            )

            continue

        regulation = candidates[0]

        rid = str(
            regulation.id
        )

        page = source["pdf_page"]

        index = source["table_index"]

        candidates_tables = (
            db_by_reg_page_index.get(
                (
                    rid,
                    page,
                    index,
                ),
                []
            )
        )

        if not candidates_tables:

            missing.append(
                {
                    "source_id":
                        source["source_id"],
                    "number":
                        source["number"],
                    "title":
                        source["title"],
                    "regulation_id":
                        rid,
                    "pdf_page":
                        page,
                    "table_index":
                        index,
                    "source_hash":
                        source["hash"],
                }
            )

            continue

        if len(candidates_tables) > 1:

            ambiguous.append(
                {
                    "source_id":
                        source["source_id"],
                    "reason":
                        "Multiple PostgreSQL tables "
                        "at same regulation/page/index.",
                    "number":
                        source["number"],
                    "title":
                        source["title"],
                    "regulation_id":
                        rid,
                    "pdf_page":
                        page,
                    "table_index":
                        index,
                    "table_ids":
                        [
                            str(x["id"])
                            for x in candidates_tables
                        ],
                }
            )

            continue

        db_table = candidates_tables[0]

        db_hash = table_hash(
            db_table["markdown"]
        )

        if db_hash != source["hash"]:

            content_mismatch.append(
                {
                    "source_id":
                        source["source_id"],
                    "number":
                        source["number"],
                    "title":
                        source["title"],
                    "regulation_id":
                        rid,
                    "pdf_page":
                        page,
                    "table_index":
                        index,
                    "source_hash":
                        source["hash"],
                    "database_hash":
                        db_hash,
                    "source_length":
                        len(
                            normalize_table_markdown(
                                source["markdown"]
                            )
                        ),
                    "database_length":
                        len(
                            normalize_table_markdown(
                                db_table["markdown"]
                            )
                        ),
                    "database_table_id":
                        str(
                            db_table["id"]
                        ),
                }
            )

            continue

        matched += 1

        source_to_db.append(
            {
                "source_id":
                    source["source_id"],
                "database_table_id":
                    str(
                        db_table["id"]
                    ),
                "number":
                    source["number"],
                "title":
                    source["title"],
                "regulation_id":
                    rid,
                "pdf_page":
                    page,
                "table_index":
                    index,
                "hash":
                    source["hash"],
            }
        )

    # --------------------------------------------------------
    # Duplicate source keys
    # --------------------------------------------------------

    source_key_groups = defaultdict(
        list
    )

    for source in source_tables:

        source_key = (
            source["key"],
            source["pdf_page"],
            source["table_index"],
            source["hash"],
        )

        source_key_groups[
            source_key
        ].append(
            source
        )

    duplicate_source_tables = []

    for key, rows in source_key_groups.items():

        if len(rows) > 1:

            duplicate_source_tables.append(
                {
                    "key":
                        list(key[:3]),
                    "hash":
                        key[3],
                    "count":
                        len(rows),
                    "source_ids":
                        [
                            x["source_id"]
                            for x in rows
                        ],
                }
            )

    if duplicate_source_tables:

        warnings.append(
            {
                "type":
                    "duplicate_source_table_definition",
                "count":
                    len(
                        duplicate_source_tables
                    ),
                "items":
                    duplicate_source_tables[:100],
            }
        )

    # --------------------------------------------------------
    # Extra PostgreSQL tables
    #
    # Determine expected DB identity:
    #
    # regulation + page + index + hash
    # --------------------------------------------------------

    source_db_identity = set()

    for source in source_tables:

        candidates = regulations_by_key.get(
            source["key"],
            [],
        )

        if len(candidates) != 1:

            continue

        rid = str(
            candidates[0].id
        )

        source_db_identity.add(
            (
                rid,
                source["pdf_page"],
                source["table_index"],
                source["hash"],
            )
        )

    extra_database_tables = []

    for table in db_tables:

        identity = (
            str(table["regulation_id"]),
            table["page_number"],
            table["table_index"],
            table_hash(
                table["markdown"]
            ),
        )

        if identity not in source_db_identity:

            extra_database_tables.append(
                {
                    "table_id":
                        str(table["id"]),
                    "regulation_id":
                        str(table["regulation_id"]),
                    "page":
                        table["page_number"],
                    "index":
                        table["table_index"],
                    "hash":
                        table_hash(
                            table["markdown"]
                        ),
                }
            )

    if extra_database_tables:

        warnings.append(
            {
                "type":
                    "extra_database_table",
                "count":
                    len(
                        extra_database_tables
                    ),
                "items":
                    extra_database_tables[:100],
            }
        )

    # --------------------------------------------------------
    # Special 5.12 check
    # --------------------------------------------------------

    check_512 = {
        "source_found":
            False,
        "database_tables":
            [],
        "content_matches":
            0,
        "content_mismatches":
            0,
    }

    for source in source_tables:

        if (
            normalize_number(
                source["number"]
            )
            != "5.12"
        ):

            continue

        if (
            normalize_title(
                source["title"]
            )
            != "aurangabad regional plan"
        ):

            continue

        check_512[
            "source_found"
        ] = True

        candidates = regulations_by_key.get(
            source["key"],
            [],
        )

        if len(candidates) != 1:

            continue

        rid = str(
            candidates[0].id
        )

        db_candidates = (
            db_by_reg_page_index.get(
                (
                    rid,
                    source["pdf_page"],
                    source["table_index"],
                ),
                [],
            )
        )

        for db_table in db_candidates:

            item = {
                "table_id":
                    str(
                        db_table["id"]
                    ),
                "regulation_id":
                    str(
                        db_table["regulation_id"]
                    ),
                "page":
                    db_table["page_number"],
                "index":
                    db_table["table_index"],
                "source_length":
                    len(
                        normalize_table_markdown(
                            source["markdown"]
                        )
                    ),
                "database_length":
                    len(
                        normalize_table_markdown(
                            db_table["markdown"]
                        )
                    ),
                "source_hash":
                    source["hash"],
                "database_hash":
                    table_hash(
                        db_table["markdown"]
                    ),
            }

            if (
                item["source_hash"]
                ==
                item["database_hash"]
            ):

                check_512[
                    "content_matches"
                ] += 1

            else:

                check_512[
                    "content_mismatches"
                ] += 1

            check_512[
                "database_tables"
            ].append(item)

    # --------------------------------------------------------
    # Failures
    # --------------------------------------------------------

    if missing:

        failures.append(
            {
                "type":
                    "missing_database_tables",
                "count":
                    len(missing),
                "items":
                    missing[:100],
            }
        )

    if content_mismatch:

        failures.append(
            {
                "type":
                    "table_content_mismatch",
                "count":
                    len(
                        content_mismatch
                    ),
                "items":
                    content_mismatch[:100],
            }
        )

    if ambiguous:

        failures.append(
            {
                "type":
                    "ambiguous_mapping",
                "count":
                    len(
                        ambiguous
                    ),
                "items":
                    ambiguous[:100],
            }
        )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    passed = (
        pdf_info.get("exists")
        and pdf_info.get("error") is None
        and source_count == database_count
        and not invalid_source_pdf_pages
        and not orphan_tables
        and not invalid_database_page_index
        and not missing
        and not content_mismatch
        and not ambiguous
    )

    return {
        "source_table_count":
            source_count,

        "database_table_count":
            database_count,

        "matched_tables":
            matched,

        "missing_tables":
            len(missing),

        "content_mismatches":
            len(content_mismatch),

        "ambiguous_mappings":
            len(ambiguous),

        "orphan_count":
            len(orphan_tables),

        "invalid_source_pdf_pages":
            len(
                invalid_source_pdf_pages
            ),

        "invalid_database_page_or_index":
            len(
                invalid_database_page_index
            ),

        "extra_database_tables":
            len(
                extra_database_tables
            ),

        "duplicate_source_definitions":
            len(
                duplicate_source_tables
            ),

        "five_point_twelve":
            check_512,

        "failures":
            failures,

        "warnings":
            warnings,

        "passed":
            passed,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Read-only verification of UDCPR "
            "PDF/source tables against PostgreSQL."
        )
    )

    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to actual UDCPR PDF.",
    )

    parser.add_argument(
        "--chunks",
        required=True,
        help="Path to udcpr_source_chunks.json.",
    )

    parser.add_argument(
        "--report",
        default=(
            "/tmp/"
            "udcpr_pdf_postgres_verification.json"
        ),
    )

    args = parser.parse_args()

    pdf_path = Path(
        args.pdf
    )

    chunks_path = Path(
        args.chunks
    )

    print()
    print("=" * 120)
    print(
        "UDCPR PDF <-> POSTGRESQL "
        "TABLE VERIFICATION"
    )
    print("=" * 120)

    print()
    print(
        "READ-ONLY MODE"
    )

    print(
        "NO DATABASE CHANGES WILL BE MADE."
    )

    print()
    print(
        "PDF    :",
        pdf_path,
    )

    print(
        "CHUNKS :",
        chunks_path,
    )

    print(
        "REPORT :",
        args.report,
    )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    pdf_info = inspect_pdf(
        pdf_path
    )

    print()
    print(
        "PDF EXISTS      :",
        pdf_info["exists"],
    )

    print(
        "PDF SIZE        :",
        pdf_info["size_bytes"],
    )

    print(
        "PDF PAGE COUNT  :",
        pdf_info["page_count"],
    )

    if pdf_info["error"]:

        print(
            "PDF ERROR       :",
            pdf_info["error"],
        )

    # --------------------------------------------------------
    # Chunks
    # --------------------------------------------------------

    chunks = load_chunks(
        str(chunks_path)
    )

    source_tables = build_source_tables(
        chunks
    )

    print()
    print(
        "SOURCE CHUNKS   :",
        len(chunks),
    )

    print(
        "SOURCE TABLES   :",
        len(source_tables),
    )

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    db = SessionLocal()

    try:

        (
            regulations,
            regulation_by_id,
            db_tables,
        ) = load_database(
            db
        )

        print()
        print(
            "REGULATIONS     :",
            len(regulations),
        )

        print(
            "DATABASE TABLES :",
            len(db_tables),
        )

        # ----------------------------------------------------
        # Verification
        # ----------------------------------------------------

        result = verify(
            pdf_info=pdf_info,
            source_tables=source_tables,
            regulations=regulations,
            regulation_by_id=regulation_by_id,
            db_tables=db_tables,
        )

    finally:

        db.close()

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    report = {
        "verification":
            "UDCPR PDF <-> PostgreSQL",

        "mode":
            "read-only",

        "pdf":
            pdf_info,

        "source":
            {
                "chunks":
                    len(chunks),

                "tables":
                    len(source_tables),

                "path":
                    str(chunks_path),
            },

        "database":
            {
                "regulations":
                    len(regulations),

                "tables":
                    len(db_tables),
            },

        "result":
            result,
    }

    with open(
        args.report,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()
    print("=" * 120)
    print(
        "VERIFICATION RESULT"
    )
    print("=" * 120)

    print(
        "Source tables       :",
        result["source_table_count"],
    )

    print(
        "Database tables     :",
        result["database_table_count"],
    )

    print(
        "Matched             :",
        result["matched_tables"],
    )

    print(
        "Missing             :",
        result["missing_tables"],
    )

    print(
        "Content mismatches  :",
        result["content_mismatches"],
    )

    print(
        "Ambiguous mappings  :",
        result["ambiguous_mappings"],
    )

    print(
        "Orphan tables       :",
        result["orphan_count"],
    )

    print(
        "Invalid PDF pages   :",
        result["invalid_source_pdf_pages"],
    )

    print(
        "Invalid page/index  :",
        result["invalid_database_page_or_index"],
    )

    print(
        "Extra DB tables     :",
        result["extra_database_tables"],
    )

    print()
    print("=" * 120)
    print(
        "5.12 AURANGABAD REGIONAL PLAN"
    )
    print("=" * 120)

    five = result[
        "five_point_twelve"
    ]

    print(
        "Source found        :",
        five["source_found"],
    )

    print(
        "Database tables     :",
        len(
            five["database_tables"]
        ),
    )

    print(
        "Content matches     :",
        five["content_matches"],
    )

    print(
        "Content mismatches  :",
        five["content_mismatches"],
    )

    for item in five[
        "database_tables"
    ]:

        print(
            "  TABLE:",
            item["table_id"],
            "| PAGE:",
            item["page"],
            "| INDEX:",
            item["index"],
            "| SOURCE LEN:",
            item["source_length"],
            "| DB LEN:",
            item["database_length"],
            "| HASH MATCH:",
            (
                item["source_hash"]
                ==
                item["database_hash"]
            ),
        )

    print()
    print("=" * 120)

    if result["passed"]:

        print(
            "VERIFICATION PASSED"
        )

        print(
            "The rebuilt PostgreSQL tables "
            "match the source table definitions."
        )

    else:

        print(
            "VERIFICATION FAILED"
        )

        print(
            "Review the failures in:"
        )

        print(
            args.report
        )

    print("=" * 120)

    print()
    print(
        "Report:",
        args.report,
    )

    print(
        "NO DATABASE CHANGES WERE MADE."
    )

    return 0 if result["passed"] else 2


if __name__ == "__main__":

    sys.exit(
        main()
    )