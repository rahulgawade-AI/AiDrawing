#!/usr/bin/env python3

"""
UDCPR canonical -> PDF -> PostgreSQL mapping audit.

READ-ONLY.
Does NOT modify PostgreSQL.
Does NOT modify Chroma.

Authoritative source:
    data/regulations/udcpr_canonical_manifest.json

PDF extraction:
    data/regulations/udcpr_source_chunks.json

Produces:
    data/regulations/udcpr_mapping_audit.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

from townplanning.infrastructure.database.session import SessionLocal


DEFAULT_MANIFEST = (
    "data/regulations/udcpr_canonical_manifest.json"
)

DEFAULT_CHUNKS = (
    "data/regulations/udcpr_source_chunks.json"
)

DEFAULT_REPORT = (
    "data/regulations/udcpr_mapping_audit.json"
)


# ============================================================
# HELPERS
# ============================================================

def clean(value: Any) -> str:

    if value is None:
        return ""

    value = str(value)

    value = value.replace("\u00a0", " ")
    value = value.replace("\u2013", "-")
    value = value.replace("\u2014", "-")

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def norm_number(value: Any) -> str:

    value = clean(value)

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

    value = re.sub(
        r"\s*\.\s*",
        ".",
        value,
    )

    return value


def norm_title(value: Any) -> str:

    value = clean(value).lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return value.strip()


def number_depth(number: str) -> int:

    number = norm_number(number)

    base = re.sub(
        r"\([A-Za-z]+\)$",
        "",
        number,
    )

    if not base:
        return 0

    return len(
        base.split(".")
    )


def is_variant(number: str) -> bool:

    return bool(
        re.search(
            r"\([A-Za-z]+\)$",
            norm_number(number),
        )
    )


def parent_number(number: str) -> str | None:

    number = norm_number(number)

    variant = re.search(
        r"^(.*)\([A-Za-z]+\)$",
        number,
    )

    if variant:
        return variant.group(1)

    parts = number.split(".")

    if len(parts) <= 1:
        return None

    return ".".join(parts[:-1])


def is_numbered_regulation(number: str) -> bool:

    return bool(
        re.fullmatch(
            r"\d+(?:\.\d+)*(?:\([A-Za-z]+\))?",
            norm_number(number),
        )
    )


def looks_like_clause(number: str) -> bool:

    number = clean(number)

    if not number:
        return True

    if re.fullmatch(
        r"\([a-z]+\)",
        number,
        re.IGNORECASE,
    ):
        return True

    if re.fullmatch(
        r"\([ivxlcdm]+\)",
        number,
        re.IGNORECASE,
    ):
        return True

    if re.fullmatch(
        r"\([a-z]+\)\([a-z]+\)",
        number,
        re.IGNORECASE,
    ):
        return True

    if re.fullmatch(
        r"\([#*0-9a-zivxlcdm]+\)",
        number,
        re.IGNORECASE,
    ):
        return True

    return False


# ============================================================
# LOAD JSON
# ============================================================

def load_json(path: str) -> Any:

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


# ============================================================
# CANONICAL MANIFEST
# ============================================================

def load_manifest(
    path: str,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:

    data = load_json(path)

    if isinstance(
        data.get("regulations"),
        list,
    ):

        entries = data["regulations"]

    elif isinstance(
        data.get("entries"),
        list,
    ):

        entries = data["entries"]

    else:

        raise RuntimeError(
            "Manifest does not contain "
            "'regulations' or 'entries'."
        )

    normalized = []

    for index, entry in enumerate(
        entries,
        start=1,
    ):

        number = norm_number(
            entry.get("number")
        )

        title = clean(
            entry.get("title")
        )

        normalized.append(
            {
                "manifest_position": index,
                "number": number,
                "title": title,
                "title_norm": norm_title(title),
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
        )

    return normalized, data


# ============================================================
# SOURCE CHUNKS
# ============================================================

def load_chunks(
    path: str,
) -> list[dict[str, Any]]:

    data = load_json(path)

    if isinstance(
        data,
        dict,
    ):

        chunks = data.get(
            "chunks",
            [],
        )

    else:

        chunks = data

    result = []

    for chunk in chunks:

        number = norm_number(
            chunk.get("number")
        )

        result.append(
            {
                **chunk,
                "number": number,
                "title_norm": norm_title(
                    chunk.get("title")
                ),
            }
        )

    return result


# ============================================================
# CANONICAL STRUCTURE
# ============================================================

def classify_canonical(
    entries: list[dict[str, Any]],
) -> dict[str, Any]:

    top = []
    sub = []
    variants = []

    by_number = {}

    for entry in entries:

        number = entry["number"]

        by_number.setdefault(
            number,
            [],
        ).append(entry)

        if is_variant(number):

            variants.append(entry)

        elif number_depth(number) == 1:

            top.append(entry)

        else:

            sub.append(entry)

    return {
        "total": len(entries),
        "top_level": top,
        "sub_regulations": sub,
        "variants": variants,
        "by_number": by_number,
    }


# ============================================================
# POSTGRES SCHEMA
# ============================================================

def inspect_database(
    db,
) -> dict[str, Any]:

    inspector = inspect(
        db.bind
    )

    tables = inspector.get_table_names()

    return {
        "tables": tables,
        "regulations_columns": (
            inspector.get_columns(
                "regulations"
            )
            if "regulations" in tables
            else []
        ),
        "regulation_tables_columns": (
            inspector.get_columns(
                "regulation_tables"
            )
            if "regulation_tables" in tables
            else []
        ),
        "tables_columns": (
            inspector.get_columns(
                "tables"
            )
            if "tables" in tables
            else []
        ),
    }


# ============================================================
# FIND ACTUAL TABLE
# ============================================================

def find_table_name(
    db,
    candidates: list[str],
) -> str | None:

    inspector = inspect(
        db.bind
    )

    actual = inspector.get_table_names()

    lower_map = {
        x.lower(): x
        for x in actual
    }

    for candidate in candidates:

        if candidate.lower() in lower_map:
            return lower_map[
                candidate.lower()
            ]

    return None


# ============================================================
# POSTGRES REGULATIONS
# ============================================================

def load_postgres_regulations(
    db,
) -> list[dict[str, Any]]:

    inspector = inspect(
        db.bind
    )

    tables = inspector.get_table_names()

    if "regulations" not in tables:

        raise RuntimeError(
            "PostgreSQL table 'regulations' "
            "was not found."
        )

    columns = {
        x["name"]
        for x in inspector.get_columns(
            "regulations"
        )
    }

    wanted = [
        "id",
        "number",
        "title",
        "chapter",
        "page_start",
        "page_end",
        "text",
    ]

    selected = [
        x
        for x in wanted
        if x in columns
    ]

    sql = (
        "SELECT "
        + ", ".join(
            '"' + x + '"'
            for x in selected
        )
        + ' FROM "regulations"'
    )

    rows = db.execute(
        text(sql)
    ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# POSTGRES TABLES
# ============================================================

def load_postgres_tables(
    db,
) -> dict[str, Any]:

    inspector = inspect(
        db.bind
    )

    tables = inspector.get_table_names()

    result = {
        "physical_table": None,
        "mapping_table": None,
        "rows": [],
        "mapping_rows": [],
    }

    physical = find_table_name(
        db,
        [
            "regulation_tables",
            "regulation_table",
        ],
    )

    generic = find_table_name(
        db,
        [
            "tables",
        ],
    )

    result["mapping_table"] = physical
    result["physical_table"] = generic

    # --------------------------------------------------------
    # regulation_tables
    # --------------------------------------------------------

    if physical:

        cols = {
            x["name"]
            for x in inspector.get_columns(
                physical
            )
        }

        selected = [
            x
            for x in [
                "id",
                "regulation_id",
                "table_id",
            ]
            if x in cols
        ]

        if selected:

            sql = (
                "SELECT "
                + ", ".join(
                    '"' + x + '"'
                    for x in selected
                )
                + f' FROM "{physical}"'
            )

            result[
                "mapping_rows"
            ] = [
                dict(x)
                for x in db.execute(
                    text(sql)
                ).mappings().all()
            ]

    # --------------------------------------------------------
    # tables
    # --------------------------------------------------------

    if generic:

        cols = {
            x["name"]
            for x in inspector.get_columns(
                generic
            )
        }

        selected = [
            x
            for x in [
                "id",
                "title",
                "page_number",
                "pdf_page",
                "content",
                "markdown",
                "table_index",
                "regulation_id",
            ]
            if x in cols
        ]

        if selected:

            sql = (
                "SELECT "
                + ", ".join(
                    '"' + x + '"'
                    for x in selected
                )
                + f' FROM "{generic}"'
            )

            result[
                "rows"
            ] = [
                dict(x)
                for x in db.execute(
                    text(sql)
                ).mappings().all()
            ]

    return result


# ============================================================
# CANONICAL -> SOURCE CHUNKS
# ============================================================

def map_canonical_to_chunks(
    canonical: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:

    chunk_map = defaultdict(list)

    for chunk in chunks:

        chunk_map[
            norm_number(
                chunk.get("number")
            )
        ].append(chunk)

    result = {}

    for number, entries in canonical[
        "by_number"
    ].items():

        matches = chunk_map.get(
            number,
            [],
        )

        result[number] = {
            "manifest_entries": entries,
            "chunk_count": len(matches),
            "chunks": matches,
            "status": (
                "mapped"
                if matches
                else "missing"
            ),
        }

    return result


# ============================================================
# POSTGRES NUMBER CLASSIFICATION
# ============================================================

def classify_postgres_rows(
    rows: list[dict[str, Any]],
    canonical_numbers: set[str],
) -> dict[str, Any]:

    canonical_rows = []
    sub_rows = []
    clause_rows = []
    false_rows = []
    unknown_rows = []

    by_number = defaultdict(list)

    for row in rows:

        raw_number = clean(
            row.get("number")
        )

        number = norm_number(
            raw_number
        )

        by_number[number].append(
            row
        )

        if number in canonical_numbers:

            canonical_rows.append(row)

            continue

        if looks_like_clause(
            raw_number
        ):

            clause_rows.append(row)

            continue

        if is_numbered_regulation(
            number
        ):

            # A numbered item which isn't in
            # the canonical manifest may be a
            # real sub-regulation, or bad data.
            sub_rows.append(row)

            continue

        false_rows.append(row)

    return {
        "canonical_rows": canonical_rows,
        "sub_rows": sub_rows,
        "clause_rows": clause_rows,
        "false_rows": false_rows,
        "unknown_rows": unknown_rows,
        "by_number": by_number,
    }


# ============================================================
# CANONICAL REGULATION MAPPING
# ============================================================

def compare_regulations(
    canonical_entries: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    pg_rows: list[dict[str, Any]],
) -> dict[str, Any]:

    canonical_by_number = defaultdict(list)

    for entry in canonical_entries:

        canonical_by_number[
            entry["number"]
        ].append(entry)

    chunk_by_number = defaultdict(list)

    for chunk in chunks:

        chunk_by_number[
            norm_number(
                chunk.get("number")
            )
        ].append(chunk)

    pg_by_number = defaultdict(list)

    for row in pg_rows:

        pg_by_number[
            norm_number(
                row.get("number")
            )
        ].append(row)

    correctly_mapped = []
    missing = []
    wrong = []
    duplicate_pg = []

    for number, entries in (
        canonical_by_number.items()
    ):

        chunks_for_number = (
            chunk_by_number.get(
                number,
                [],
            )
        )

        pg_for_number = (
            pg_by_number.get(
                number,
                [],
            )
        )

        if not pg_for_number:

            missing.append(
                {
                    "number": number,
                    "manifest_entries": entries,
                    "source_chunks": len(
                        chunks_for_number
                    ),
                }
            )

            continue

        if len(pg_for_number) > len(
            entries
        ):

            duplicate_pg.append(
                {
                    "number": number,
                    "expected_entries": len(
                        entries
                    ),
                    "postgres_rows": len(
                        pg_for_number
                    ),
                    "rows": pg_for_number,
                }
            )

        matched_entries = []

        for entry in entries:

            title_norm = entry[
                "title_norm"
            ]

            candidates = [
                row
                for row in pg_for_number
                if norm_title(
                    row.get("title")
                ) == title_norm
            ]

            if candidates:

                matched_entries.append(
                    {
                        "manifest": entry,
                        "postgres": candidates[
                            0
                        ],
                    }
                )

            else:

                wrong.append(
                    {
                        "number": number,
                        "manifest": entry,
                        "postgres_candidates": pg_for_number,
                    }
                )

        if len(matched_entries) == len(
            entries
        ):

            correctly_mapped.append(
                {
                    "number": number,
                    "matches": matched_entries,
                }
            )

    return {
        "correctly_mapped": correctly_mapped,
        "missing": missing,
        "wrong": wrong,
        "duplicate_postgres": duplicate_pg,
    }


# ============================================================
# SUB-REGULATION AUDIT
# ============================================================

def audit_sub_regulations(
    pg_rows: list[dict[str, Any]],
    canonical_numbers: set[str],
) -> dict[str, Any]:

    sub_rows = []

    for row in pg_rows:

        number = norm_number(
            row.get("number")
        )

        if not is_numbered_regulation(
            number
        ):
            continue

        if number in canonical_numbers:
            continue

        if number_depth(number) <= 1:
            continue

        sub_rows.append(row)

    orphan = []
    legitimate = []

    for row in sub_rows:

        number = norm_number(
            row.get("number")
        )

        parent = parent_number(
            number
        )

        if parent in canonical_numbers:

            legitimate.append(
                {
                    "row": row,
                    "parent": parent,
                }
            )

        else:

            orphan.append(
                {
                    "row": row,
                    "expected_parent": parent,
                }
            )

    return {
        "total_sub_regulation_rows": len(
            sub_rows
        ),
        "legitimate_sub_regulations": legitimate,
        "orphan_sub_regulations": orphan,
    }


# ============================================================
# TABLE AUDIT
# ============================================================

def audit_tables(
    chunks: list[dict[str, Any]],
    pg_tables: dict[str, Any],
    pg_rows: list[dict[str, Any]],
) -> dict[str, Any]:

    # --------------------------------------------------------
    # Expected PDF tables
    # --------------------------------------------------------

    expected = []

    for chunk in chunks:

        number = norm_number(
            chunk.get("number")
        )

        for table in (
            chunk.get("tables")
            or []
        ):

            expected.append(
                {
                    "regulation_number": number,
                    "pdf_page": table.get(
                        "pdf_page"
                    ),
                    "table_index": table.get(
                        "table_index"
                    ),
                    "title": clean(
                        table.get("title")
                    ),
                    "markdown": table.get(
                        "markdown"
                    )
                    or "",
                }
            )

    # --------------------------------------------------------
    # Actual PostgreSQL tables
    # --------------------------------------------------------

    actual = pg_tables.get(
        "rows",
        [],
    )

    mapping_rows = pg_tables.get(
        "mapping_rows",
        [],
    )

    pg_by_id = {
        str(x.get("id")): x
        for x in actual
    }

    regulation_by_id = {
        str(x.get("id")): x
        for x in pg_rows
    }

    mapped_actual = []

    for mapping in mapping_rows:

        table_id = mapping.get(
            "table_id"
        )

        regulation_id = mapping.get(
            "regulation_id"
        )

        table = pg_by_id.get(
            str(table_id)
        )

        regulation = regulation_by_id.get(
            str(regulation_id)
        )

        mapped_actual.append(
            {
                "mapping": mapping,
                "table": table,
                "regulation": regulation,
            }
        )

    # --------------------------------------------------------
    # Determine counts
    # --------------------------------------------------------

    expected_count = len(
        expected
    )

    actual_count = len(
        actual
    )

    mapped_count = len(
        mapped_actual
    )

    # --------------------------------------------------------
    # Page + title based approximate matching
    # --------------------------------------------------------

    matched = []
    missing = []

    used_actual = set()

    for exp_index, exp in enumerate(
        expected
    ):

        exp_md = norm_title(
            exp["markdown"]
        )

        candidates = []

        for index, item in enumerate(
            mapped_actual
        ):

            if index in used_actual:
                continue

            table = item.get(
                "table"
            ) or {}

            regulation = item.get(
                "regulation"
            ) or {}

            actual_page = (
                table.get("pdf_page")
                or table.get("page_number")
            )

            actual_reg_number = (
                norm_number(
                    regulation.get(
                        "number"
                    )
                )
                if regulation
                else ""
            )

            page_match = (
                actual_page
                == exp["pdf_page"]
            )

            reg_match = (
                actual_reg_number
                == exp[
                    "regulation_number"
                ]
            )

            actual_md = norm_title(
                table.get(
                    "markdown"
                )
                or table.get(
                    "content"
                )
                or ""
            )

            content_match = (
                bool(exp_md)
                and bool(actual_md)
                and (
                    exp_md[:180]
                    in actual_md
                    or actual_md[:180]
                    in exp_md
                )
            )

            score = (
                int(page_match) * 4
                + int(reg_match) * 5
                + int(content_match) * 3
            )

            if score:
                candidates.append(
                    (
                        score,
                        index,
                        item,
                    )
                )

        if not candidates:

            missing.append(exp)

            continue

        candidates.sort(
            reverse=True,
            key=lambda x: x[0],
        )

        score, index, item = (
            candidates[0]
        )

        used_actual.add(index)

        if (
            item.get("regulation")
            and norm_number(
                item["regulation"].get(
                    "number"
                )
            )
            != exp[
                "regulation_number"
            ]
        ):

            matched.append(
                {
                    "expected": exp,
                    "actual": item,
                    "status": "wrong_parent",
                }
            )

        else:

            matched.append(
                {
                    "expected": exp,
                    "actual": item,
                    "status": "matched",
                }
            )

    extra = []

    for index, item in enumerate(
        mapped_actual
    ):

        if index not in used_actual:

            extra.append(item)

    wrong_parent = [
        x
        for x in matched
        if x["status"]
        == "wrong_parent"
    ]

    correct = [
        x
        for x in matched
        if x["status"]
        == "matched"
    ]

    return {
        "expected_pdf_tables": expected_count,
        "postgres_table_rows": actual_count,
        "postgres_mapping_rows": mapped_count,
        "correct_table_mappings": len(
            correct
        ),
        "wrong_table_parent": len(
            wrong_parent
        ),
        "missing_tables": len(
            missing
        ),
        "extra_tables": len(
            extra
        ),
        "wrong_parent_details": wrong_parent,
        "missing_details": missing,
        "extra_details": extra,
    }


# ============================================================
# TEXT COVERAGE
# ============================================================

def audit_text_coverage(
    canonical_entries: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    pg_rows: list[dict[str, Any]],
) -> dict[str, Any]:

    chunk_map = defaultdict(list)

    for chunk in chunks:

        chunk_map[
            norm_number(
                chunk.get("number")
            )
        ].append(chunk)

    pg_map = defaultdict(list)

    for row in pg_rows:

        pg_map[
            norm_number(
                row.get("number")
            )
        ].append(row)

    result = []

    for entry in canonical_entries:

        number = entry[
            "number"
        ]

        source_text = "\n".join(
            clean(
                c.get(
                    "regulation_text"
                )
            )
            for c in chunk_map.get(
                number,
                [],
            )
        ).strip()

        pg_text = "\n".join(
            clean(
                r.get("text")
            )
            for r in pg_map.get(
                number,
                [],
            )
        ).strip()

        result.append(
            {
                "number": number,
                "source_length": len(
                    source_text
                ),
                "postgres_length": len(
                    pg_text
                ),
                "source_pages": sorted(
                    {
                        p
                        for c in chunk_map.get(
                            number,
                            [],
                        )
                        for p in (
                            c.get(
                                "source_pages"
                            )
                            or []
                        )
                    }
                ),
                "empty_source": not bool(
                    source_text
                ),
                "empty_postgres": not bool(
                    pg_text
                ),
                "length_ratio": (
                    round(
                        len(pg_text)
                        / len(source_text),
                        4,
                    )
                    if source_text
                    else None
                ),
            }
        )

    return {
        "entries": result,
        "empty_source": [
            x
            for x in result
            if x["empty_source"]
        ],
        "empty_postgres": [
            x
            for x in result
            if x["empty_postgres"]
        ],
    }


# ============================================================
# MAIN AUDIT
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Read-only UDCPR "
            "canonical/PostgreSQL "
            "mapping audit."
        )
    )

    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
    )

    parser.add_argument(
        "--chunks",
        default=DEFAULT_CHUNKS,
    )

    parser.add_argument(
        "--report",
        default=DEFAULT_REPORT,
    )

    args = parser.parse_args()

    print()
    print("=" * 110)
    print("UDCPR CANONICAL -> PDF -> POSTGRES MAPPING AUDIT")
    print("=" * 110)
    print("READ ONLY")
    print()

    # --------------------------------------------------------
    # Load source
    # --------------------------------------------------------

    entries, manifest = load_manifest(
        args.manifest
    )

    chunks = load_chunks(
        args.chunks
    )

    structure = classify_canonical(
        entries
    )

    canonical_numbers = set(
        structure["by_number"].keys()
    )

    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    db = SessionLocal()

    try:

        schema = inspect_database(
            db
        )

        pg_rows = load_postgres_regulations(
            db
        )

        pg_tables = load_postgres_tables(
            db
        )

    finally:

        db.close()

    # --------------------------------------------------------
    # Comparisons
    # --------------------------------------------------------

    canonical_chunk_map = (
        map_canonical_to_chunks(
            structure,
            chunks,
        )
    )

    regulation_comparison = (
        compare_regulations(
            entries,
            chunks,
            pg_rows,
        )
    )

    pg_classification = (
        classify_postgres_rows(
            pg_rows,
            canonical_numbers,
        )
    )

    sub_audit = (
        audit_sub_regulations(
            pg_rows,
            canonical_numbers,
        )
    )

    table_audit = audit_tables(
        chunks,
        pg_tables,
        pg_rows,
    )

    text_audit = audit_text_coverage(
        entries,
        chunks,
        pg_rows,
    )

    # --------------------------------------------------------
    # False top-level fragments
    # --------------------------------------------------------

    false_top_level = []

    for row in pg_classification[
        "false_rows"
    ]:

        false_top_level.append(
            {
                "id": row.get("id"),
                "number": row.get(
                    "number"
                ),
                "title": row.get(
                    "title"
                ),
                "page_start": row.get(
                    "page_start"
                ),
                "page_end": row.get(
                    "page_end"
                ),
            }
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary = {
        "canonical_structure": {
            "total_manifest_entries": structure[
                "total"
            ],
            "top_level_regulations": len(
                structure[
                    "top_level"
                ]
            ),
            "sub_regulations": len(
                structure[
                    "sub_regulations"
                ]
            ),
            "variants": len(
                structure[
                    "variants"
                ]
            ),
            "clauses": (
                len(
                    pg_classification[
                        "clause_rows"
                    ]
                )
            ),
            "tables": table_audit[
                "expected_pdf_tables"
            ],
        },
        "postgres": {
            "total_regulation_rows": len(
                pg_rows
            ),
            "top_level_correctly_mapped": len(
                regulation_comparison[
                    "correctly_mapped"
                ]
            ),
            "missing_canonical_regulations": len(
                regulation_comparison[
                    "missing"
                ]
            ),
            "wrong_canonical_mappings": len(
                regulation_comparison[
                    "wrong"
                ]
            ),
            "duplicate_canonical_rows": len(
                regulation_comparison[
                    "duplicate_postgres"
                ]
            ),
            "legitimate_sub_regulations": sub_audit[
                "total_sub_regulation_rows"
            ],
            "orphan_sub_regulations": len(
                sub_audit[
                    "orphan_sub_regulations"
                ]
            ),
            "false_top_level_fragments": len(
                false_top_level
            ),
            "postgres_tables": table_audit[
                "postgres_table_rows"
            ],
            "correct_table_mappings": table_audit[
                "correct_table_mappings"
            ],
            "wrong_table_parent": table_audit[
                "wrong_table_parent"
            ],
            "missing_tables": table_audit[
                "missing_tables"
            ],
            "extra_tables": table_audit[
                "extra_tables"
            ],
        },
    }

    # --------------------------------------------------------
    # Human-readable console output
    # --------------------------------------------------------

    print("=" * 95)
    print("CANONICAL STRUCTURE")
    print("-" * 95)

    print(
        "Top-level regulations       :",
        summary[
            "canonical_structure"
        ]["top_level_regulations"],
    )

    print(
        "Sub-regulations             :",
        summary[
            "canonical_structure"
        ]["sub_regulations"],
    )

    print(
        "Variants                    :",
        summary[
            "canonical_structure"
        ]["variants"],
    )

    print(
        "Clauses                     :",
        summary[
            "canonical_structure"
        ]["clauses"],
    )

    print(
        "Tables                      :",
        summary[
            "canonical_structure"
        ]["tables"],
    )

    print()

    print("=" * 95)
    print("POSTGRES")
    print("-" * 95)

    pg = summary[
        "postgres"
    ]

    print(
        "Total regulation rows       :",
        pg["total_regulation_rows"],
    )

    print(
        "Top-level correctly mapped  :",
        pg[
            "top_level_correctly_mapped"
        ],
    )

    print(
        "Missing canonical regs     :",
        pg[
            "missing_canonical_regulations"
        ],
    )

    print(
        "Wrong canonical mappings   :",
        pg[
            "wrong_canonical_mappings"
        ],
    )

    print(
        "Duplicate canonical rows   :",
        pg[
            "duplicate_canonical_rows"
        ],
    )

    print(
        "Legitimate sub-regulations :",
        pg[
            "legitimate_sub_regulations"
        ],
    )

    print(
        "Orphan sub-regulations     :",
        pg[
            "orphan_sub_regulations"
        ],
    )

    print(
        "False top-level fragments  :",
        pg[
            "false_top_level_fragments"
        ],
    )

    print(
        "Postgres tables             :",
        pg[
            "postgres_tables"
        ],
    )

    print(
        "Correct table mappings      :",
        pg[
            "correct_table_mappings"
        ],
    )

    print(
        "Wrong table parent          :",
        pg[
            "wrong_table_parent"
        ],
    )

    print(
        "Missing tables              :",
        pg[
            "missing_tables"
        ],
    )

    print(
        "Extra tables                :",
        pg[
            "extra_tables"
        ],
    )

    # --------------------------------------------------------
    # Important details
    # --------------------------------------------------------

    print()

    if false_top_level:

        print("=" * 95)
        print(
            "FALSE / NON-CANONICAL POSTGRES ROWS"
        )
        print("-" * 95)

        for row in false_top_level[:30]:

            print(
                f'{row["number"]!r:15} | '
                f'{clean(row["title"])[:100]}'
            )

        if len(false_top_level) > 30:

            print(
                "...",
                len(false_top_level) - 30,
                "more"
            )

    if sub_audit[
        "orphan_sub_regulations"
    ]:

        print()

        print("=" * 95)
        print("ORPHAN SUB-REGULATIONS")
        print("-" * 95)

        for item in sub_audit[
            "orphan_sub_regulations"
        ][:30]:

            row = item["row"]

            print(
                f'{row.get("number")!r:15} | '
                f'parent={item["expected_parent"]!r} | '
                f'{clean(row.get("title"))[:80]}'
            )

    if table_audit[
        "wrong_parent_details"
    ]:

        print()

        print("=" * 95)
        print("WRONG TABLE PARENTS")
        print("-" * 95)

        for item in table_audit[
            "wrong_parent_details"
        ][:30]:

            exp = item["expected"]
            actual = item["actual"]

            regulation = (
                actual.get(
                    "regulation"
                )
                or {}
            )

            print(
                "EXPECTED:",
                exp[
                    "regulation_number"
                ],
                "PDF:",
                exp["pdf_page"],
                "| ACTUAL:",
                regulation.get(
                    "number"
                ),
            )

    # --------------------------------------------------------
    # Write report
    # --------------------------------------------------------

    report = {
        "summary": summary,
        "database_schema": {
            "tables": schema[
                "tables"
            ],
            "regulations_columns": [
                x["name"]
                for x in schema[
                    "regulations_columns"
                ]
            ],
            "regulation_tables_columns": [
                x["name"]
                for x in schema[
                    "regulation_tables_columns"
                ]
            ],
            "tables_columns": [
                x["name"]
                for x in schema[
                    "tables_columns"
                ]
            ],
        },
        "canonical_to_chunks": canonical_chunk_map,
        "regulation_comparison": (
            regulation_comparison
        ),
        "postgres_classification": {
            "clause_rows": pg_classification[
                "clause_rows"
            ],
            "false_rows": pg_classification[
                "false_rows"
            ],
        },
        "sub_regulation_audit": sub_audit,
        "table_audit": table_audit,
        "text_audit": text_audit,
        "manifest_document_structure": manifest.get(
            "document_structure",
            {},
        ),
    }

    report_path = Path(
        args.report
    )

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

    print()
    print("=" * 95)
    print("AUDIT COMPLETE")
    print("=" * 95)
    print("Report:", report_path)
    print()
    print(
        "NO DATABASE CHANGES WERE MADE."
    )


if __name__ == "__main__":
    main()
