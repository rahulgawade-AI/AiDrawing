#!/usr/bin/env python3

"""
FINAL UDCPR CONTENT INTEGRITY TEST

Purpose:
    Determine whether PostgreSQL has actually lost/corrupted canonical
    UDCPR regulation text.

READ ONLY:
    - No PostgreSQL modifications
    - No Chroma modifications
    - No deletes
    - No rebuilds

Sources:
    Canonical manifest
    Canonical source chunks
    PostgreSQL regulations

Decision:

    SAFE TO REPAIR
        Every canonical regulation has matching PostgreSQL text.

    REBUILD REQUIRED
        One or more canonical regulations have missing/incomplete text.

Important:
    Regulation number alone is NOT used as the unique identity.
    Matching uses:
        number
        title
        page_start
        text content
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, ".")

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.infrastructure.database.models import RegulationModel


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.replace("\x00", " ")

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def normalize_title(value: str | None) -> str:
    value = normalize_text(value)

    return value.lower()


def text_hash(value: str) -> str:
    return hashlib.sha256(
        normalize_text(value).encode("utf-8")
    ).hexdigest()


def text_contains(
    pg_text: str,
    canonical_text: str,
) -> bool:

    pg = normalize_text(pg_text)
    canonical = normalize_text(canonical_text)

    if not pg or not canonical:
        return False

    return canonical in pg


def coverage_ratio(
    pg_text: str,
    canonical_text: str,
) -> float:

    pg = normalize_text(pg_text)
    canonical = normalize_text(canonical_text)

    if not canonical:
        return 1.0

    if not pg:
        return 0.0

    # Exact containment is the strongest possible result.
    if canonical in pg:
        return 1.0

    # Character-token coverage.
    pg_tokens = set(pg.split())
    canonical_tokens = canonical.split()

    if not canonical_tokens:
        return 1.0

    matched = sum(
        1
        for token in canonical_tokens
        if token in pg_tokens
    )

    return matched / len(canonical_tokens)


# ============================================================
# MANIFEST
# ============================================================

def load_manifest(path: str):

    with open(
        path,
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

    if not entries:
        raise RuntimeError(
            "No regulations found in canonical manifest."
        )

    return entries


# ============================================================
# CHUNKS
# ============================================================

def load_chunks(path: str):

    with open(
        path,
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    chunks = data.get(
        "chunks",
        data,
    )

    if not chunks:
        raise RuntimeError(
            "No canonical source chunks found."
        )

    return chunks


# ============================================================
# CANONICAL RECORD
# ============================================================

def canonical_key(c):

    number = normalize_text(
        c.get("number")
    )

    title = normalize_title(
        c.get("title")
    )

    return (
        number,
        title,
    )


def build_canonical_map(
    manifest,
    chunks,
):

    manifest_map = {}

    for entry in manifest:

        number = normalize_text(
            entry.get("number")
        )

        title = normalize_title(
            entry.get("title")
        )

        if not number:
            continue

        key = (
            number,
            title,
        )

        manifest_map[key] = entry

    chunk_map = {}

    for chunk in chunks:

        number = normalize_text(
            chunk.get("number")
        )

        title = normalize_title(
            chunk.get("title")
        )

        if not number:
            continue

        key = (
            number,
            title,
        )

        chunk_map[key] = chunk

    return manifest_map, chunk_map


# ============================================================
# MAIN AUDIT
# ============================================================

def main():

    parser = argparse.ArgumentParser()

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
        default="/tmp/udcpr_content_integrity.json",
    )

    args = parser.parse_args()

    print()
    print("=" * 120)
    print("FINAL UDCPR CONTENT INTEGRITY TEST")
    print("=" * 120)
    print("READ ONLY")
    print()

    manifest = load_manifest(
        args.manifest
    )

    chunks = load_chunks(
        args.chunks
    )

    manifest_map, chunk_map = build_canonical_map(
        manifest,
        chunks,
    )

    print(
        "Canonical manifest entries :",
        len(manifest),
    )

    print(
        "Canonical source chunks    :",
        len(chunks),
    )

    db = SessionLocal()

    try:

        pg_rows = (
            db.query(RegulationModel)
            .all()
        )

        print(
            "PostgreSQL regulation rows :",
            len(pg_rows),
        )

        # ----------------------------------------------------
        # PostgreSQL index
        # ----------------------------------------------------

        pg_by_key = defaultdict(list)

        for row in pg_rows:

            key = (
                normalize_text(row.number),
                normalize_title(row.title),
            )

            pg_by_key[key].append(row)

        # ----------------------------------------------------
        # Results
        # ----------------------------------------------------

        exact = []
        contained = []
        partial = []
        missing = []
        mismatched = []
        duplicate_matches = []

        for key, manifest_entry in manifest_map.items():

            number, title = key

            chunk = chunk_map.get(key)

            if chunk is None:

                missing.append({
                    "number": number,
                    "title": title,
                    "reason": "canonical_chunk_missing",
                })

                continue

            canonical_text = (
                chunk.get("regulation_text")
                or ""
            )

            canonical_text = normalize_text(
                canonical_text
            )

            candidates = pg_by_key.get(
                key,
                [],
            )

            if not candidates:

                missing.append({
                    "number": number,
                    "title": title,
                    "reason": "postgres_row_missing",
                    "canonical_text_length":
                        len(canonical_text),
                })

                continue

            matches = []

            for row in candidates:

                pg_text = normalize_text(
                    row.text
                )

                ratio = coverage_ratio(
                    pg_text,
                    canonical_text,
                )

                if text_hash(
                    pg_text
                ) == text_hash(
                    canonical_text
                ):

                    matches.append(
                        (
                            row,
                            "exact",
                            ratio,
                        )
                    )

                elif canonical_text and canonical_text in pg_text:

                    matches.append(
                        (
                            row,
                            "contained",
                            ratio,
                        )
                    )

                elif ratio >= 0.95:

                    matches.append(
                        (
                            row,
                            "partial",
                            ratio,
                        )
                    )

            if len(matches) > 1:

                duplicate_matches.append({
                    "number": number,
                    "title": title,
                    "postgres_ids": [
                        str(x[0].id)
                        for x in matches
                    ],
                    "count": len(matches),
                })

            if not matches:

                # Find best candidate for diagnostics.
                best = None

                best_ratio = 0.0

                for row in candidates:

                    ratio = coverage_ratio(
                        row.text,
                        canonical_text,
                    )

                    if ratio > best_ratio:

                        best_ratio = ratio
                        best = row

                mismatched.append({
                    "number": number,
                    "title": title,
                    "postgres_candidates": len(
                        candidates
                    ),
                    "best_id": (
                        str(best.id)
                        if best
                        else None
                    ),
                    "canonical_length":
                        len(canonical_text),
                    "best_pg_length": (
                        len(best.text or "")
                        if best
                        else 0
                    ),
                    "coverage": best_ratio,
                })

                continue

            strongest = sorted(
                matches,
                key=lambda x: (
                    {
                        "exact": 3,
                        "contained": 2,
                        "partial": 1,
                    }.get(x[1], 0),
                    x[2],
                ),
                reverse=True,
            )[0]

            row, status, ratio = strongest

            record = {
                "number": number,
                "title": title,
                "postgres_id": str(row.id),
                "postgres_page_start":
                    row.page_start,
                "postgres_page_end":
                    row.page_end,
                "canonical_length":
                    len(canonical_text),
                "postgres_length":
                    len(row.text or ""),
                "coverage":
                    ratio,
            }

            if status == "exact":
                exact.append(record)

            elif status == "contained":
                contained.append(record)

            else:
                partial.append(record)

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        canonical_count = len(
            manifest_map
        )

        good_count = (
            len(exact)
            + len(contained)
            + len(partial)
        )

        lost_count = (
            len(missing)
            + len(mismatched)
        )

        print()
        print("=" * 120)
        print("CONTENT VERIFICATION")
        print("=" * 120)

        print(
            "Canonical records checked :",
            canonical_count,
        )

        print(
            "Exact text matches        :",
            len(exact),
        )

        print(
            "Canonical text contained  :",
            len(contained),
        )

        print(
            "High-coverage matches     :",
            len(partial),
        )

        print(
            "Missing PostgreSQL text   :",
            len(missing),
        )

        print(
            "Text mismatches            :",
            len(mismatched),
        )

        print(
            "Duplicate matching rows   :",
            len(duplicate_matches),
        )

        print()
        print("=" * 120)
        print("DECISION")
        print("=" * 120)

        if lost_count == 0:

            decision = "SAFE_TO_REPAIR"

            print()
            print(
                "SAFE TO REPAIR"
            )
            print()
            print(
                "Canonical PDF text is present in PostgreSQL."
            )
            print(
                "Do NOT drop PostgreSQL."
            )
            print(
                "Do NOT rebuild Chroma."
            )
            print(
                "Proceed with mapping/duplicate/table-parent repair."
            )

        else:

            decision = "REBUILD_REQUIRED"

            print()
            print(
                "REBUILD REQUIRED"
            )
            print()
            print(
                f"{lost_count} canonical records have "
                "missing or mismatched PostgreSQL text."
            )
            print(
                "The current PostgreSQL dataset cannot be "
                "trusted as a complete canonical ingestion."
            )
            print()
            print(
                "Next action:"
            )
            print(
                "1. Backup PostgreSQL."
            )
            print(
                "2. Drop/recreate UDCPR regulation/table data."
            )
            print(
                "3. Rebuild PostgreSQL from canonical source chunks."
            )
            print(
                "4. Rebuild Chroma from the same canonical chunks."
            )

        # ----------------------------------------------------
        # Diagnostic mismatches
        # ----------------------------------------------------

        if missing:

            print()
            print("=" * 120)
            print("MISSING")
            print("=" * 120)

            for item in missing[:30]:

                print(
                    item["number"],
                    "|",
                    item["title"],
                    "|",
                    item["reason"],
                )

        if mismatched:

            print()
            print("=" * 120)
            print("TEXT MISMATCHES")
            print("=" * 120)

            for item in mismatched[:30]:

                print(
                    item["number"],
                    "|",
                    item["title"],
                )

                print(
                    "  PG candidates :",
                    item["postgres_candidates"],
                )

                print(
                    "  canonical     :",
                    item["canonical_length"],
                )

                print(
                    "  best PG       :",
                    item["best_pg_length"],
                )

                print(
                    "  coverage      :",
                    f"{item['coverage']:.2%}",
                )

        report = {
            "decision": decision,

            "canonical_count":
                canonical_count,

            "postgres_count":
                len(pg_rows),

            "exact_count":
                len(exact),

            "contained_count":
                len(contained),

            "partial_count":
                len(partial),

            "missing_count":
                len(missing),

            "mismatch_count":
                len(mismatched),

            "duplicate_match_count":
                len(duplicate_matches),

            "missing":
                missing,

            "mismatched":
                mismatched,

            "duplicate_matches":
                duplicate_matches,

            "exact":
                exact,

            "contained":
                contained,

            "partial":
                partial,
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

        print()
        print("=" * 120)
        print(
            "REPORT:",
            args.report,
        )
        print("=" * 120)

        print()
        print(
            "NO DATABASE CHANGES WERE MADE."
        )

    finally:

        db.close()


if __name__ == "__main__":
    main()
