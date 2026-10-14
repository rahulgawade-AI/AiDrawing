#!/usr/bin/env python3
"""
Verify that the EXISTING ChromaDB contains regulatory text AND table content.

This script is READ-ONLY:
- does not rebuild Chroma
- does not delete anything
- does not access PostgreSQL
- uses the existing project Chroma path/collection

It checks:
1. total Chroma records
2. metadata coverage
3. records containing table markers
4. records containing headers/rows
5. records containing regulatory numeric values
6. sample searches for FSI, setback, parking, height, fire
7. regulation-number coverage
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

import chromadb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROMA_PATH = PROJECT_ROOT / "data" / "chroma"
COLLECTION_NAME = "townplanning"

# Existing project collection is known to use 768-dimensional embeddings.
# We do not create an embedding function here because this audit primarily
# inspects the stored records directly.
BATCH_SIZE = 250

TABLE_MARKERS = (
    "TABLE TITLE:",
    "HEADERS:",
    "ROWS:",
    "MARKDOWN:",
    "TABLE ",
)

FIELD_PATTERNS = {
    "fsi": re.compile(
        r"\b(?:basic\s+fsi|permissible\s+fsi|premium\s+fsi|"
        r"tdr\s+fsi|maximum\s+(?:building\s+)?potential|"
        r"maximum\s+fsi|fsi\s+on\s+payment)\b",
        re.I,
    ),
    "setback": re.compile(
        r"\b(?:setback|set\s*back|margin|margins|marginal\s+distance)\b",
        re.I,
    ),
    "parking": re.compile(
        r"\bparking\b|\bcar\s+parking\b|\bscooter\b|\bvisitor\s+parking\b",
        re.I,
    ),
    "height": re.compile(
        r"\b(?:building\s+height|maximum\s+height|height\s+of\s+building|"
        r"storeys?|stories?)\b",
        re.I,
    ),
    "fire": re.compile(
        r"\b(?:fire\s+safety|fire\s+access|fire\s+service|"
        r"chief\s+fire|fire\s+brigade|fire\s+fighting)\b",
        re.I,
    ),
    "road_width": re.compile(
        r"\broad\s+width\b|\broad\s+width\s*\(m",
        re.I,
    ),
}

REGULATION_PATTERNS = (
    re.compile(r"\bUDCPR\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)+)", re.I),
    re.compile(r"\bregulation\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)+)", re.I),
    re.compile(r"\bregulation_number\s*[:=]\s*([0-9]+(?:\.[0-9]+)+)", re.I),
)


def regulation_numbers(metadata, document):
    found = set()

    if isinstance(metadata, dict):
        for key in (
            "regulation_number",
            "regulationNumber",
            "regulation",
            "number",
        ):
            value = metadata.get(key)
            if value is not None:
                text = str(value).strip()
                if re.fullmatch(r"\d+(?:\.\d+)+", text):
                    found.add(text)

    text = str(document or "")
    for pattern in REGULATION_PATTERNS:
        found.update(pattern.findall(text))

    return found


def main():
    print("=" * 90)
    print("READ-ONLY CHROMA REGULATORY CONTENT AUDIT")
    print("=" * 90)
    print(f"Path       : {CHROMA_PATH}")
    print(f"Collection : {COLLECTION_NAME}")
    print()

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection(name=COLLECTION_NAME)

    total = collection.count()
    print(f"TOTAL RECORDS: {total}")

    if total == 0:
        print("\nRESULT: FAIL - Chroma collection is empty.")
        return 2

    all_ids = []
    all_docs = []
    all_meta = []

    for offset in range(0, total, BATCH_SIZE):
        result = collection.get(
            limit=min(BATCH_SIZE, total - offset),
            offset=offset,
            include=["documents", "metadatas"],
        )
        all_ids.extend(result.get("ids") or [])
        all_docs.extend(result.get("documents") or [])
        all_meta.extend(result.get("metadatas") or [])

    print(f"READ BACK  : {len(all_docs)}")

    if len(all_docs) != total:
        print("RESULT: FAIL - could not read every Chroma record.")
        return 2

    # ------------------------------------------------------------------
    # Metadata / document integrity
    # ------------------------------------------------------------------
    missing_docs = []
    missing_regulation_metadata = []
    empty_docs = []

    regulation_counter = Counter()
    table_records = []
    field_records = defaultdict(list)

    for i, document in enumerate(all_docs):
        metadata = all_meta[i] if i < len(all_meta) else {}
        text = str(document or "")

        if not text.strip():
            empty_docs.append(all_ids[i])
            continue

        numbers = regulation_numbers(metadata, text)

        if not numbers:
            missing_regulation_metadata.append(all_ids[i])

        for number in numbers:
            regulation_counter[number] += 1

        upper = text.upper()
        if any(marker in upper for marker in TABLE_MARKERS):
            table_records.append(i)

        for field, pattern in FIELD_PATTERNS.items():
            if pattern.search(text):
                field_records[field].append(i)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    print()
    print("CONTENT INTEGRITY")
    print("-" * 90)
    print(f"Empty documents                  : {len(empty_docs)}")
    print(f"Records without regulation ID   : {len(missing_regulation_metadata)}")
    print(f"Records containing table markers : {len(table_records)}")

    for field in FIELD_PATTERNS:
        print(f"Records containing {field:12s}: {len(field_records[field])}")

    print()
    print("REGULATION COVERAGE")
    print("-" * 90)
    print(f"Unique regulation numbers found : {len(regulation_counter)}")

    for number, count in sorted(
        regulation_counter.items(),
        key=lambda x: tuple(int(p) for p in x[0].split(".")),
    ):
        print(f"{number:12s} records={count}")

    # ------------------------------------------------------------------
    # Show actual table examples.
    # ------------------------------------------------------------------
    print()
    print("TABLE CONTENT SAMPLES")
    print("-" * 90)

    shown = 0
    for i in table_records:
        metadata = all_meta[i] if i < len(all_meta) else {}
        text = str(all_docs[i] or "")

        numbers = regulation_numbers(metadata, text)
        print()
        print(f"ID          : {all_ids[i]}")
        print(f"Regulation  : {', '.join(sorted(numbers)) or 'UNKNOWN'}")
        print(f"Metadata    : {metadata}")

        # Print the first useful table section, not the entire document.
        lines = text.splitlines()
        useful = []
        inside = False

        for line in lines:
            if re.search(r"TABLE TITLE:|HEADERS:|ROWS:|MARKDOWN:", line, re.I):
                inside = True
            if inside:
                useful.append(line)
            if inside and len(useful) >= 18:
                break

        print("Content:")
        print("\n".join(useful)[:5000])

        shown += 1
        if shown >= 10:
            break

    # ------------------------------------------------------------------
    # Targeted semantic-free content checks.
    # These inspect stored Chroma documents, so they do not depend on the
    # query embedding function.
    # ------------------------------------------------------------------
    print()
    print("FIELD COVERAGE")
    print("-" * 90)

    for field, indexes in field_records.items():
        print(f"{field:12s}: {'YES' if indexes else 'NO'}")

    # Strong table check: table records must contain actual row/header data,
    # not merely the word "table".
    strong_tables = 0
    weak_tables = 0

    for i in table_records:
        text = str(all_docs[i] or "")
        has_header = bool(re.search(r"\bHEADERS:\b", text, re.I))
        has_rows = bool(re.search(r"\bROWS:\b", text, re.I))
        has_markdown = bool(re.search(r"\bMARKDOWN:\b", text, re.I))

        if (has_header and has_rows) or has_markdown:
            strong_tables += 1
        else:
            weak_tables += 1

    print()
    print("TABLE QUALITY")
    print("-" * 90)
    print(f"Records with strong table structure : {strong_tables}")
    print(f"Records with weak table markers     : {weak_tables}")

    # ------------------------------------------------------------------
    # Final verdict.
    # ------------------------------------------------------------------
    print()
    print("=" * 90)

    if empty_docs:
        print("RESULT: FAIL - empty Chroma documents exist.")
        return 1

    if strong_tables == 0:
        print("RESULT: FAIL - no structured table content was found in Chroma.")
        return 1

    if not field_records["fsi"]:
        print("RESULT: FAIL - no FSI content found in Chroma.")
        return 1

    if not field_records["setback"]:
        print("RESULT: WARNING - no setback/margin content found in Chroma.")

    if not field_records["parking"]:
        print("RESULT: WARNING - no parking content found in Chroma.")

    if not field_records["height"]:
        print("RESULT: WARNING - no building-height content found in Chroma.")

    print("RESULT: PASS - Chroma contains regulatory text and structured table content.")
    print()
    print("Important:")
    print("- This proves the stored Chroma records contain the content.")
    print("- It does NOT yet prove every individual PDF/table row is present.")
    print("- For complete row-for-row verification, compare the expected source-table")
    print("  inventory against these Chroma records.")
    print("- No PostgreSQL access was used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
