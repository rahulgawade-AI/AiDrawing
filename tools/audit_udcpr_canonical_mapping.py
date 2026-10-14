#!/usr/bin/env python3

"""
UDCPR CANONICAL MAPPING AUDIT
=============================

READ ONLY.

This script compares:

    Canonical manifest
          |
          v
    Canonical source chunks
          |
          v
    PostgreSQL regulations
          |
          v
    PostgreSQL tables

It DOES NOT:
    - delete PostgreSQL rows
    - update PostgreSQL rows
    - insert PostgreSQL rows
    - modify Chroma

The purpose is to determine whether the existing PostgreSQL
database can be repaired or whether a clean rebuild is required.

Important:
    UDCPR numbering is hierarchical.

Examples:

    1.0       top-level
    1.1       top-level
    1.3       top-level
    1.3.1     child of 1.3
    2.2       top-level
    2.2.1     child of 2.2
    2.2.5(a)  variant of 2.2.5
    7.1       top-level
    7.1.x     child of 7.1

Clauses such as:

    (a)
    (b)
    A)
    B)
    C)

are NOT automatically treated as regulations.

Usage:

    python tools/audit_udcpr_canonical_mapping.py \
        --manifest data/regulations/udcpr_canonical_manifest.json \
        --chunks data/regulations/udcpr_source_chunks.json \
        --report /tmp/udcpr_canonical_mapping.json

"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, ".")

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.infrastructure.database.models import (
    RegulationModel,
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_space(value: str | None) -> str:
    if not value:
        return ""

    value = value.replace("\u00a0", " ")

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def normalize_text(value: str | None) -> str:
    value = value or ""

    value = value.replace(
        "\u00a0",
        " ",
    )

    value = value.replace(
        "\r\n",
        "\n",
    )

    value = value.replace(
        "\r",
        "\n",
    )

    # Remove common PDF soft artifacts.
    value = re.sub(
        r"-\n(?=\w)",
        "",
        value,
    )

    # Normalize line whitespace.
    value = re.sub(
        r"[ \t]+",
        " ",
        value,
    )

    # Normalize blank lines.
    value = re.sub(
        r"\n+",
        "\n",
        value,
    )

    return value.strip()


def normalized_compare_text(
    value: str | None,
) -> str:

    value = normalize_text(value)

    # For comparison only.
    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip().lower()


def text_hash(
    value: str | None,
) -> str:

    normalized = normalized_compare_text(
        value
    )

    return hashlib.sha256(
        normalized.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# REGULATION NUMBER PARSING
# ============================================================

NUMBER_RE = re.compile(
    r"^(?P<number>\d+(?:\.\d+)*)(?P<variant>\([a-z]\))?$",
    re.IGNORECASE,
)


def canonical_key(
    number: str,
) -> str:

    number = normalize_space(number)

    # Remove spaces around variants.
    number = re.sub(
        r"\s+(\([a-z]\))$",
        r"\1",
        number,
        flags=re.IGNORECASE,
    )

    return number


def parse_number(
    number: str,
) -> tuple[str | None, str | None]:

    number = canonical_key(number)

    match = NUMBER_RE.fullmatch(
        number
    )

    if not match:
        return None, None

    base = match.group(
        "number"
    )

    variant = match.group(
        "variant"
    )

    if variant:
        variant = variant.lower()

    return base, variant


def is_canonical_number(
    number: str,
) -> bool:

    base, variant = parse_number(
        number
    )

    return base is not None


def number_depth(
    number: str,
) -> int | None:

    base, _ = parse_number(
        number
    )

    if not base:
        return None

    return len(
        base.split(".")
    )


def is_variant(
    number: str,
) -> bool:

    base, variant = parse_number(
        number
    )

    return (
        base is not None
        and variant is not None
    )


def parent_number(
    number: str,
) -> str | None:

    base, variant = parse_number(
        number
    )

    if base is None:
        return None

    if variant:
        return base

    parts = base.split(".")

    if len(parts) <= 2:
        return None

    return ".".join(
        parts[:-1]
    )


def is_top_level(
    number: str,
) -> bool:

    base, variant = parse_number(
        number
    )

    if base is None:
        return False

    if variant:
        return False

    return len(
        base.split(".")
    ) == 2


def is_sub_regulation(
    number: str,
) -> bool:

    base, variant = parse_number(
        number
    )

    if base is None:
        return False

    if variant:
        return False

    return len(
        base.split(".")
    ) >= 3


# ============================================================
# MANIFEST LOADING
# ============================================================

def load_json(
    path: str,
) -> Any:

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def load_manifest(
    path: str,
) -> list[dict[str, Any]]:

    data = load_json(path)

    if isinstance(data, list):
        entries = data

    elif isinstance(data, dict):

        entries = (
            data.get("regulations")
            or data.get("entries")
            or data.get("items")
            or []
        )

    else:
        raise RuntimeError(
            "Unsupported manifest format."
        )

    if not isinstance(
        entries,
        list,
    ):
        raise RuntimeError(
            "Manifest entries are not a list."
        )

    return entries


def load_chunks(
    path: str,
) -> list[dict[str, Any]]:

    data = load_json(path)

    if isinstance(data, list):
        chunks = data

    elif isinstance(data, dict):

        chunks = (
            data.get("chunks")
            or data.get("entries")
            or []
        )

    else:
        raise RuntimeError(
            "Unsupported chunks format."
        )

    return chunks


# ============================================================
# MANIFEST STRUCTURE
# ============================================================

@dataclass
class CanonicalEntry:

    number: str
    title: str
    printed_page_start: int | None
    printed_page_end: int | None
    variant: str | None
    chapter: str | None

    @property
    def key(self) -> str:
        return canonical_key(
            self.number
        )

    @property
    def base_number(self) -> str | None:
        base, _ = parse_number(
            self.key
        )
        return base

    @property
    def is_variant(self) -> bool:
        return is_variant(
            self.key
        )

    @property
    def top_level(self) -> bool:
        return is_top_level(
            self.key
        )

    @property
    def sub_regulation(self) -> bool:
        return is_sub_regulation(
            self.key
        )


def convert_manifest_entry(
    raw: dict[str, Any],
) -> CanonicalEntry | None:

    number = (
        raw.get("number")
        or raw.get("regulation_number")
        or raw.get("id")
    )

    if not number:
        return None

    number = canonical_key(
        str(number)
    )

    title = normalize_space(
        raw.get("title")
        or raw.get("name")
        or ""
    )

    start = (
        raw.get("printed_page_start")
        or raw.get("page_start")
        or raw.get("page")
    )

    end = (
        raw.get("printed_page_end")
        or raw.get("page_end")
    )

    variant = raw.get(
        "variant"
    )

    if variant:
        variant = str(
            variant
        ).lower()

        if not variant.startswith("("):
            variant = (
                "("
                + variant
                + ")"
            )

    return CanonicalEntry(
        number=number,
        title=title,
        printed_page_start=(
            int(start)
            if start is not None
            else None
        ),
        printed_page_end=(
            int(end)
            if end is not None
            else None
        ),
        variant=variant,
        chapter=(
            str(
                raw.get("chapter")
            )
            if raw.get("chapter")
            is not None
            else None
        ),
    )


# ============================================================
# CHUNK INDEX
# ============================================================

def build_chunk_index(
    chunks: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:

    result = defaultdict(list)

    for chunk in chunks:

        number = (
            chunk.get("number")
            or chunk.get(
                "regulation_number"
            )
        )

        if not number:
            continue

        key = canonical_key(
            str(number)
        )

        result[key].append(
            chunk
        )

    return dict(result)


# ============================================================
# POSTGRES REPRESENTATION
# ============================================================

def postgres_rows(
    db,
) -> list[RegulationModel]:

    return (
        db.query(
            RegulationModel
        )
        .order_by(
            RegulationModel.number,
            RegulationModel.title,
            RegulationModel.page_start,
            RegulationModel.page_end,
        )
        .all()
    )


def row_key(
    row: RegulationModel,
) -> str:

    return canonical_key(
        row.number
    )


def title_similarity(
    a: str,
    b: str,
) -> float:

    a = normalized_compare_text(
        a
    )

    b = normalized_compare_text(
        b
    )

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    if a in b:
        return 0.90

    if b in a:
        return 0.90

    a_words = set(
        a.split()
    )

    b_words = set(
        b.split()
    )

    if not a_words or not b_words:
        return 0.0

    return len(
        a_words & b_words
    ) / len(
        a_words | b_words
    )


def page_overlap(
    row: RegulationModel,
    entry: CanonicalEntry,
) -> bool:

    if (
        entry.printed_page_start
        is None
    ):
        return False

    start = (
        entry.printed_page_start
    )

    end = (
        entry.printed_page_end
        or start
    )

    row_start = (
        row.page_start
    )

    row_end = (
        row.page_end
    )

    return not (
        row_end < start
        or row_start > end
    )


# ============================================================
# MATCH CANONICAL -> POSTGRES
# ============================================================

def find_best_rows(
    entry: CanonicalEntry,
    rows_by_number: dict[
        str,
        list[RegulationModel],
    ],
) -> list[
    tuple[
        RegulationModel,
        float,
        str,
    ]
]:

    candidates = rows_by_number.get(
        entry.key,
        []
    )

    scored = []

    for row in candidates:

        score = 0.0
        reasons = []

        ts = title_similarity(
            entry.title,
            row.title,
        )

        score += ts * 50

        if ts >= 0.95:
            reasons.append(
                "title_exact"
            )

        elif ts >= 0.75:
            reasons.append(
                "title_similar"
            )

        if page_overlap(
            row,
            entry,
        ):

            score += 30

            reasons.append(
                "page_overlap"
            )

        if (
            entry.printed_page_start
            == row.page_start
        ):

            score += 10

            reasons.append(
                "page_start_exact"
            )

        if (
            entry.printed_page_end
            and entry.printed_page_end
            == row.page_end
        ):

            score += 10

            reasons.append(
                "page_end_exact"
            )

        scored.append(
            (
                row,
                score,
                ",".join(reasons),
            )
        )

    scored.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    return scored


# ============================================================
# TEXT VERIFICATION
# ============================================================

def compare_source_chunk(
    entry: CanonicalEntry,
    chunk_index: dict[
        str,
        list[dict[str, Any]],
    ],
) -> dict[str, Any]:

    chunks = chunk_index.get(
        entry.key,
        []
    )

    if not chunks:

        return {
            "found": False,
            "chunk_count": 0,
            "text_match": False,
            "source_text_length": 0,
        }

    texts = []

    source_pages = set()

    tables = 0

    for chunk in chunks:

        text = (
            chunk.get(
                "regulation_text"
            )
            or chunk.get("text")
            or ""
        )

        texts.append(
            text
        )

        for page in (
            chunk.get(
                "source_pages"
            )
            or []
        ):

            try:
                source_pages.add(
                    int(page)
                )
            except Exception:
                pass

        table_list = (
            chunk.get(
                "tables"
            )
            or []
        )

        tables += len(
            table_list
        )

    combined = "\n".join(
        texts
    )

    return {
        "found": True,
        "chunk_count": len(
            chunks
        ),
        "text_match": True,
        "source_text_length": len(
            combined
        ),
        "source_text_hash": text_hash(
            combined
        ),
        "source_pages": sorted(
            source_pages
        ),
        "table_count": tables,
    }


# ============================================================
# DATABASE TABLE AUDIT
# ============================================================

def load_tables(
    db,
) -> list[Any]:

    # Import only here so the script remains usable
    # if the table model name differs.
    try:
        from townplanning.infrastructure.database.models import (
            TableModel,
        )
    except ImportError:

        return []

    return (
        db.query(
            TableModel
        )
        .order_by(
            TableModel.page_number,
            TableModel.table_index,
        )
        .all()
    )


def table_content_hash(
    table,
) -> str:

    payload = {
        "page_number": getattr(
            table,
            "page_number",
            None,
        ),
        "table_index": getattr(
            table,
            "table_index",
            None,
        ),
        "title": getattr(
            table,
            "title",
            None,
        ),
        "headers": getattr(
            table,
            "headers",
            None,
        ),
        "rows": getattr(
            table,
            "rows",
            None,
        ),
        "markdown": getattr(
            table,
            "markdown",
            None,
        ),
    }

    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )

    return hashlib.sha256(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# TABLE SOURCE EXTRACTION
# ============================================================

def source_tables(
    chunk: dict[str, Any],
) -> list[dict[str, Any]]:

    tables = (
        chunk.get(
            "tables"
        )
        or []
    )

    if not isinstance(
        tables,
        list,
    ):
        return []

    return tables


def canonical_table_inventory(
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    result = []

    for chunk in chunks:

        number = (
            chunk.get("number")
            or chunk.get(
                "regulation_number"
            )
        )

        if not number:
            continue

        number = canonical_key(
            str(number)
        )

        for table in source_tables(
            chunk
        ):

            result.append(
                {
                    "regulation_number": number,
                    "page_number": (
                        table.get(
                            "pdf_page"
                        )
                        or table.get(
                            "page_number"
                        )
                    ),
                    "table_index": (
                        table.get(
                            "table_index"
                        )
                    ),
                    "title": normalize_space(
                        table.get(
                            "title"
                        )
                        or ""
                    ),
                    "headers": (
                        table.get(
                            "headers"
                        )
                            or []
                    ),
                    "rows": (
                        table.get(
                            "rows"
                        )
                            or []
                    ),
                    "markdown": (
                        table.get(
                            "markdown"
                        )
                        or ""
                    ),
                }
            )

    return result


# ============================================================
# MAIN AUDIT
# ============================================================

def run_audit(
    manifest_path: str,
    chunks_path: str,
) -> dict[str, Any]:

    print()
    print("=" * 110)
    print(
        "UDCPR CANONICAL -> PDF -> POSTGRES MAPPING AUDIT"
    )
    print("=" * 110)
    print(
        "READ ONLY"
    )

    raw_manifest = load_manifest(
        manifest_path
    )

    raw_chunks = load_chunks(
        chunks_path
    )

    canonical_entries = []

    for raw in raw_manifest:

        entry = convert_manifest_entry(
            raw
        )

        if entry:
            canonical_entries.append(
                entry
            )

    # --------------------------------------------------------
    # Canonical classification
    # --------------------------------------------------------

    canonical_top = [
        e
        for e in canonical_entries
        if e.top_level
    ]

    canonical_sub = [
        e
        for e in canonical_entries
        if e.sub_regulation
    ]

    canonical_variants = [
        e
        for e in canonical_entries
        if e.is_variant
    ]

    canonical_clauses = []

    for raw in raw_manifest:

        number = str(
            raw.get("number", "")
        )

        if (
            number
            and not is_canonical_number(
                number
            )
        ):

            canonical_clauses.append(
                raw
            )

    chunks_by_number = build_chunk_index(
        raw_chunks
    )

    canonical_tables = (
        canonical_table_inventory(
            raw_chunks
        )
    )

    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    db = SessionLocal()

    try:

        rows = postgres_rows(
            db
        )

        rows_by_number = defaultdict(
            list
        )

        for row in rows:

            rows_by_number[
                row_key(row)
            ].append(
                row
            )

        tables = load_tables(
            db
        )

        # ----------------------------------------------------
        # Canonical -> PostgreSQL mapping
        # ----------------------------------------------------

        canonical_results = []

        matched_row_ids = set()

        missing = []
        wrong = []
        duplicates = []

        correct_top = []
        correct_sub = []
        correct_variants = []

        text_mismatch = []

        for entry in canonical_entries:

            candidates = find_best_rows(
                entry,
                rows_by_number,
            )

            source = compare_source_chunk(
                entry,
                chunks_by_number,
            )

            if not candidates:

                missing.append(
                    {
                        "number": entry.key,
                        "title": entry.title,
                        "page_start": (
                            entry.printed_page_start
                        ),
                        "page_end": (
                            entry.printed_page_end
                        ),
                        "source": source,
                    }
                )

                canonical_results.append(
                    {
                        "number": entry.key,
                        "title": entry.title,
                        "status": "missing",
                        "source": source,
                        "candidates": [],
                    }
                )

                continue

            best_row, score, reason = (
                candidates[0]
            )

            matched_row_ids.add(
                str(best_row.id)
            )

            duplicate_candidates = (
                candidates[1:]
            )

            if duplicate_candidates:

                duplicates.append(
                    {
                        "number": entry.key,
                        "title": entry.title,
                        "matched_id": str(
                            best_row.id
                        ),
                        "duplicate_ids": [
                            str(
                                x[0].id
                            )
                            for x in duplicate_candidates
                        ],
                        "duplicate_count": len(
                            duplicate_candidates
                        ),
                    }
                )

            title_ok = (
                title_similarity(
                    entry.title,
                    best_row.title,
                )
                >= 0.90
            )

            page_ok = page_overlap(
                best_row,
                entry,
            )

            source_hash = (
                source.get(
                    "source_text_hash"
                )
            )

            postgres_hash = text_hash(
                best_row.text
            )

            text_ok = (
                source_hash is None
                or source_hash
                == postgres_hash
            )

            status = "correct"

            if not title_ok:

                status = "wrong_title"

            elif not page_ok:

                status = "wrong_page"

            elif not text_ok:

                status = "text_mismatch"

                text_mismatch.append(
                    {
                        "number": entry.key,
                        "postgres_id": str(
                            best_row.id
                        ),
                        "postgres_text_length": len(
                            best_row.text
                            or ""
                        ),
                        "source_text_length": source.get(
                            "source_text_length",
                            0,
                        ),
                        "postgres_hash": postgres_hash,
                        "source_hash": source_hash,
                    }
                )

            result = {
                "number": entry.key,
                "title": entry.title,
                "postgres_id": str(
                    best_row.id
                ),
                "postgres_number": (
                    best_row.number
                ),
                "postgres_title": (
                    best_row.title
                ),
                "postgres_page_start": (
                    best_row.page_start
                ),
                "postgres_page_end": (
                    best_row.page_end
                ),
                "score": score,
                "match_reason": reason,
                "title_ok": title_ok,
                "page_ok": page_ok,
                "text_ok": text_ok,
                "status": status,
                "source": source,
            }

            canonical_results.append(
                result
            )

            if status == "correct":

                if entry.top_level:
                    correct_top.append(
                        entry.key
                    )

                elif entry.sub_regulation:
                    correct_sub.append(
                        entry.key
                    )

                elif entry.is_variant:
                    correct_variants.append(
                        entry.key
                    )

            elif status != "correct":

                wrong.append(
                    result
                )

        # ----------------------------------------------------
        # PostgreSQL classification
        # ----------------------------------------------------

        false_fragments = []
        orphan_subs = []

        postgres_canonical_numbers = {
            e.key
            for e in canonical_entries
        }

        for row in rows:

            key = row_key(
                row
            )

            if key in postgres_canonical_numbers:
                continue

            base, variant = parse_number(
                key
            )

            # ------------------------------------------------
            # Variant / malformed clause-like numbers
            # ------------------------------------------------

            if not is_canonical_number(
                key
            ):

                false_fragments.append(
                    {
                        "id": str(
                            row.id
                        ),
                        "number": row.number,
                        "title": row.title,
                        "page_start": row.page_start,
                        "page_end": row.page_end,
                        "reason": (
                            "non-canonical-number"
                        ),
                    }
                )

                continue

            # ------------------------------------------------
            # A syntactically valid child may still be
            # orphaned if its parent is absent from canonical.
            # ------------------------------------------------

            if is_sub_regulation(
                key
            ):

                parent = parent_number(
                    key
                )

                if (
                    parent is None
                    or parent
                    not in postgres_canonical_numbers
                ):

                    orphan_subs.append(
                        {
                            "id": str(
                                row.id
                            ),
                            "number": row.number,
                            "parent": parent,
                            "title": row.title,
                            "page_start": row.page_start,
                            "page_end": row.page_end,
                            "reason": (
                                "canonical parent missing"
                            ),
                        }
                    )

                    continue

            # ------------------------------------------------
            # Anything else is a non-canonical fragment.
            # ------------------------------------------------

            false_fragments.append(
                {
                    "id": str(
                        row.id
                    ),
                    "number": row.number,
                    "title": row.title,
                    "page_start": row.page_start,
                    "page_end": row.page_end,
                    "reason": (
                        "not present in canonical manifest"
                    ),
                }
            )

        # ----------------------------------------------------
        # Duplicate PostgreSQL rows
        # ----------------------------------------------------

        duplicate_groups = []

        for number, group in rows_by_number.items():

            if len(group) <= 1:
                continue

            duplicate_groups.append(
                {
                    "number": number,
                    "count": len(group),
                    "rows": [
                        {
                            "id": str(
                                row.id
                            ),
                            "title": row.title,
                            "page_start": row.page_start,
                            "page_end": row.page_end,
                            "text_length": len(
                                row.text
                                or ""
                            ),
                        }
                        for row in group
                    ],
                }
            )

        # ----------------------------------------------------
        # Table parent mapping
        # ----------------------------------------------------

        table_parent_correct = 0
        table_parent_wrong = 0
        table_orphans = 0

        table_mapping = []

        canonical_regulation_ids = {
            r["number"]: r.get(
                "postgres_id"
            )
            for r in canonical_results
            if r.get("postgres_id")
        }

        for table in tables:

            regulation_id = str(
                table.regulation_id
            )

            matched_number = None

            for number, rid in (
                canonical_regulation_ids.items()
            ):

                if str(rid) == regulation_id:

                    matched_number = number
                    break

            if matched_number:

                table_parent_correct += 1

                table_mapping.append(
                    {
                        "table_id": str(
                            table.id
                        ),
                        "regulation_id": regulation_id,
                        "canonical_number": matched_number,
                        "page_number": table.page_number,
                        "table_index": table.table_index,
                        "status": "correct_parent",
                    }
                )

            else:

                table_orphans += 1

                table_mapping.append(
                    {
                        "table_id": str(
                            table.id
                        ),
                        "regulation_id": regulation_id,
                        "page_number": table.page_number,
                        "table_index": table.table_index,
                        "status": "orphan_parent",
                    }
                )

        # ----------------------------------------------------
        # Source table -> PostgreSQL table comparison
        # ----------------------------------------------------

        postgres_table_keys = Counter()

        for table in tables:

            postgres_table_keys[
                (
                    table.page_number,
                    table.table_index,
                )
            ] += 1

        canonical_table_keys = Counter()

        for table in canonical_tables:

            page = table.get(
                "page_number"
            )

            index = table.get(
                "table_index"
            )

            if page is not None:
                canonical_table_keys[
                    (
                        int(page),
                        index,
                    )
                ] += 1

        missing_tables = []
        extra_tables = []

        for key, count in (
            canonical_table_keys.items()
        ):

            if (
                postgres_table_keys.get(
                    key,
                    0,
                )
                < count
            ):

                missing_tables.append(
                    {
                        "page_number": key[0],
                        "table_index": key[1],
                        "expected_count": count,
                        "postgres_count": postgres_table_keys.get(
                            key,
                            0,
                        ),
                    }
                )

        for key, count in (
            postgres_table_keys.items()
        ):

            if (
                canonical_table_keys.get(
                    key,
                    0,
                )
                < count
            ):

                extra_tables.append(
                    {
                        "page_number": key[0],
                        "table_index": key[1],
                        "postgres_count": count,
                        "canonical_count": canonical_table_keys.get(
                            key,
                            0,
                        ),
                    }
                )

        # ----------------------------------------------------
        # Structural summary
        # ----------------------------------------------------

        report = {

            "read_only": True,

            "inputs": {
                "manifest": manifest_path,
                "chunks": chunks_path,
            },

            "canonical": {
                "total_entries": len(
                    canonical_entries
                ),
                "top_level": len(
                    canonical_top
                ),
                "sub_regulations": len(
                    canonical_sub
                ),
                "variants": len(
                    canonical_variants
                ),
                "clauses": len(
                    canonical_clauses
                ),
                "tables": len(
                    canonical_tables
                ),
            },

            "postgres": {
                "regulation_rows": len(
                    rows
                ),
                "table_rows": len(
                    tables
                ),
            },

            "mapping": {

                "canonical_correct": len(
                    [
                        x
                        for x in canonical_results
                        if x["status"]
                        == "correct"
                    ]
                ),

                "top_level_correct": len(
                    correct_top
                ),

                "sub_regulations_correct": len(
                    correct_sub
                ),

                "variants_correct": len(
                    correct_variants
                ),

                "missing_canonical": len(
                    missing
                ),

                "wrong_canonical": len(
                    wrong
                ),

                "duplicate_canonical": len(
                    duplicates
                ),

                "duplicate_number_groups": len(
                    duplicate_groups
                ),

                "orphan_sub_regulations": len(
                    orphan_subs
                ),

                "false_top_level_or_fragments": len(
                    false_fragments
                ),

                "text_mismatches": len(
                    text_mismatch
                ),

                "table_parent_correct": table_parent_correct,

                "table_parent_wrong": table_parent_wrong,

                "table_orphans": table_orphans,

                "missing_tables": len(
                    missing_tables
                ),

                "extra_tables": len(
                    extra_tables
                ),
            },

            "canonical_entries": canonical_results,

            "missing": missing,

            "wrong": wrong,

            "text_mismatches": text_mismatch,

            "duplicate_canonical": duplicates,

            "duplicate_number_groups": duplicate_groups,

            "orphan_sub_regulations": orphan_subs,

            "false_fragments": false_fragments,

            "table_mapping": table_mapping,

            "missing_tables": missing_tables,

            "extra_tables": extra_tables,
        }

        return report

    finally:

        db.close()


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_summary(
    report: dict[str, Any],
    report_path: str,
):

    c = report[
        "canonical"
    ]

    p = report[
        "postgres"
    ]

    m = report[
        "mapping"
    ]

    print()
    print("=" * 110)
    print(
        "CANONICAL STRUCTURE"
    )
    print("-" * 110)

    print(
        f"Top-level regulations       : {c['top_level']}"
    )

    print(
        f"Sub-regulations             : {c['sub_regulations']}"
    )

    print(
        f"Variants                    : {c['variants']}"
    )

    print(
        f"Clauses                     : {c['clauses']}"
    )

    print(
        f"Tables                      : {c['tables']}"
    )

    print()
    print("=" * 110)
    print(
        "POSTGRES"
    )
    print("-" * 110)

    print(
        f"Regulation rows             : {p['regulation_rows']}"
    )

    print(
        f"Postgres tables             : {p['table_rows']}"
    )

    print()
    print("=" * 110)
    print(
        "MAPPING"
    )
    print("-" * 110)

    print(
        f"Canonical correctly mapped  : {m['canonical_correct']}"
    )

    print(
        f"Top-level correctly mapped  : {m['top_level_correct']}"
    )

    print(
        f"Sub-regulations mapped      : {m['sub_regulations_correct']}"
    )

    print(
        f"Variants mapped             : {m['variants_correct']}"
    )

    print(
        f"Missing canonical regs     : {m['missing_canonical']}"
    )

    print(
        f"Wrong canonical mappings   : {m['wrong_canonical']}"
    )

    print(
        f"Duplicate canonical rows   : {m['duplicate_canonical']}"
    )

    print(
        f"Duplicate number groups    : {m['duplicate_number_groups']}"
    )

    print(
        f"Orphan sub-regulations     : {m['orphan_sub_regulations']}"
    )

    print(
        f"False fragments            : {m['false_top_level_or_fragments']}"
    )

    print(
        f"Text mismatches            : {m['text_mismatches']}"
    )

    print(
        f"Correct table parents      : {m['table_parent_correct']}"
    )

    print(
        f"Wrong table parents        : {m['table_parent_wrong']}"
    )

    print(
        f"Orphan tables              : {m['table_orphans']}"
    )

    print(
        f"Missing tables             : {m['missing_tables']}"
    )

    print(
        f"Extra tables               : {m['extra_tables']}"
    )

    # --------------------------------------------------------
    # Important examples
    # --------------------------------------------------------

    wrong = report[
        "wrong"
    ]

    if wrong:

        print()
        print("=" * 110)
        print(
            "FIRST 20 WRONG / MISMATCHED CANONICAL ENTRIES"
        )
        print("-" * 110)

        for item in wrong[:20]:

            print(
                f"{item['number']:15} | "
                f"{item['status']:15} | "
                f"PG={item['postgres_id']} | "
                f"{item['title'][:80]}"
            )

    false = report[
        "false_fragments"
    ]

    if false:

        print()
        print("=" * 110)
        print(
            "FIRST 30 NON-CANONICAL POSTGRES ROWS"
        )
        print("-" * 110)

        for item in false[:30]:

            print(
                f"{item['number']!r:25} | "
                f"{item['title'][:90]}"
            )

    orphan = report[
        "orphan_sub_regulations"
    ]

    if orphan:

        print()
        print("=" * 110)
        print(
            "FIRST 30 ORPHAN SUB-REGULATIONS"
        )
        print("-" * 110)

        for item in orphan[:30]:

            print(
                f"{item['number']!r:25} | "
                f"parent={item['parent']!r:15} | "
                f"{item['title'][:80]}"
            )

    print()
    print("=" * 110)
    print(
        "AUDIT COMPLETE"
    )
    print("=" * 110)

    print(
        f"Report: {report_path}"
    )

    print()
    print(
        "NO DATABASE CHANGES WERE MADE."
    )


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Read-only UDCPR canonical "
            "PostgreSQL mapping audit."
        )
    )

    parser.add_argument(
        "--manifest",
        default=(
            "data/regulations/"
            "udcpr_canonical_manifest.json"
        ),
    )

    parser.add_argument(
        "--chunks",
        default=(
            "data/regulations/"
            "udcpr_source_chunks.json"
        ),
    )

    parser.add_argument(
        "--report",
        default=(
            "data/regulations/"
            "udcpr_canonical_mapping_audit.json"
        ),
    )

    args = parser.parse_args()

    report = run_audit(
        args.manifest,
        args.chunks,
    )

    report_path = Path(
        args.report
    )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        report_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print_summary(
        report,
        str(report_path),
    )


if __name__ == "__main__":
    main()
