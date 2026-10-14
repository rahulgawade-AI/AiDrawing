#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import chromadb

from townplanning.core.settings import get_settings
from townplanning.infrastructure.database.session import SessionLocal
from townplanning.infrastructure.database.models.rule_model import RuleModel

# Try the project's regulation ORM model.
try:
    from townplanning.infrastructure.database.models.regulation_model import (
        RegulationModel,
    )
except ImportError:
    try:
        from townplanning.infrastructure.database.models import RegulationModel
    except ImportError:
        RegulationModel = None


OUTPUT_DIR = Path("/tmp/udcpr_database_mapping")


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(value: Any) -> str:
    if value is None:
        return ""

    value = str(value).strip().lower()

    # Normalize whitespace.
    value = re.sub(r"\s+", " ", value)

    # Normalize common punctuation around regulation numbers.
    value = value.replace("–", "-")
    value = value.replace("—", "-")

    return value.strip()


def normalize_regulation_number(value: Any) -> str:
    """
    Normalize regulation numbers such as:

        6.4
        6.4
        6.4 *
        Regulation 6.4

    into:

        6.4
    """

    value = normalize(value)

    if not value:
        return ""

    value = re.sub(
        r"^regulation\s*(no\.?|number)?\s*",
        "",
        value,
    )

    value = value.strip(" *:-.")

    match = re.search(
        r"\b(\d+(?:\.\d+)+)\b",
        value,
    )

    if match:
        return match.group(1)

    return value


def normalize_title(value: Any) -> str:
    value = normalize(value)

    if not value:
        return ""

    value = re.sub(
        r"^regulation\s*(no\.?|number)?\s*[\d.]+\s*",
        "",
        value,
    )

    value = re.sub(
        r"^[\d.]+\s*[\-*:]?\s*",
        "",
        value,
    )

    value = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# ============================================================
# JSON SAFE
# ============================================================

def json_safe(value: Any) -> Any:
    """
    Convert SQLAlchemy / arbitrary values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(k): json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            json_safe(v)
            for v in value
        ]

    return str(value)


# ============================================================
# CHROMA
# ============================================================

def load_chroma():
    settings = get_settings()

    print()
    print("=" * 80)
    print("CHROMA")
    print("=" * 80)

    print("Path       :", settings.CHROMA_PATH)
    print("Collection :", settings.CHROMA_COLLECTION)

    client = chromadb.PersistentClient(
        path=settings.CHROMA_PATH
    )

    collection = client.get_collection(
        name=settings.CHROMA_COLLECTION
    )

    count = collection.count()

    print("Records    :", count)

    result = collection.get(
        limit=count,
        include=[
            "documents",
            "metadatas",
        ],
    )

    ids = result.get("ids") or []
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    records = []

    for index, chroma_id in enumerate(ids):

        document = (
            documents[index]
            if index < len(documents)
            else ""
        )

        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        metadata = metadata or {}

        regulation_id = (
            metadata.get("regulation_id")
            or metadata.get("regulationId")
            or metadata.get("regulationID")
            or metadata.get("regulation_uuid")
            or metadata.get("regulationUuid")
            or metadata.get("regulation_model_id")
            or metadata.get("regulationModelId")
        )

        regulation_number = (
            metadata.get("regulation_number")
            or metadata.get("regulationNumber")
            or metadata.get("number")
        )

        title = (
            metadata.get("title")
            or metadata.get("regulation_title")
            or metadata.get("regulationTitle")
        )

        record = {
            "chroma_id": chroma_id,
            "regulation_id": (
                str(regulation_id).strip()
                if regulation_id is not None
                else None
            ),
            "regulation_number": (
                str(regulation_number).strip()
                if regulation_number is not None
                else None
            ),
            "title": (
                str(title).strip()
                if title is not None
                else None
            ),
            "start_page": metadata.get("start_page"),
            "end_page": metadata.get("end_page"),
            "chapter_number": metadata.get("chapter_number"),
            "chapter_title": metadata.get("chapter_title"),
            "language": metadata.get("language"),
            "metadata": json_safe(metadata),
            "document": document or "",
        }

        records.append(record)

    return records


# ============================================================
# POSTGRESQL
# ============================================================

def load_postgres():
    print()
    print("=" * 80)
    print("POSTGRESQL")
    print("=" * 80)

    session = SessionLocal()

    try:
        rules = session.query(RuleModel).all()

        print("Rules      :", len(rules))

        rule_rows = []

        for rule in rules:

            metadata = getattr(
                rule,
                "metadata",
                None,
            )

            if metadata is None:
                metadata = getattr(
                    rule,
                    "metadata_json",
                    {},
                )

            rule_rows.append(
                {
                    "id": rule.id,
                    "regulation_id": rule.regulation_id,
                    "category": rule.category,
                    "name": rule.name,
                    "description": rule.description,
                    "condition": json_safe(
                        getattr(
                            rule,
                            "condition_json",
                            {},
                        )
                    ),
                    "result": json_safe(
                        getattr(
                            rule,
                            "result_json",
                            {},
                        )
                    ),
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "metadata": json_safe(metadata or {}),
                }
            )

        regulation_rows = []

        if RegulationModel is not None:

            regulations = (
                session
                .query(RegulationModel)
                .all()
            )

            print(
                "Regulations:",
                len(regulations),
            )

            for regulation in regulations:

                number = (
                    getattr(
                        regulation,
                        "number",
                        None,
                    )
                    or getattr(
                        regulation,
                        "regulation_number",
                        None,
                    )
                )

                title = getattr(
                    regulation,
                    "title",
                    None,
                )

                regulation_rows.append(
                    {
                        "id": str(
                            getattr(
                                regulation,
                                "id",
                                "",
                            )
                        ),
                        "number": number,
                        "title": title,
                        "chapter": (
                            getattr(
                                regulation,
                                "chapter",
                                None,
                            )
                        ),
                        "page_start": (
                            getattr(
                                regulation,
                                "page_start",
                                None,
                            )
                            or getattr(
                                regulation,
                                "start_page",
                                None,
                            )
                        ),
                        "page_end": (
                            getattr(
                                regulation,
                                "page_end",
                                None,
                            )
                            or getattr(
                                regulation,
                                "end_page",
                                None,
                            )
                        ),
                        "source_document": (
                            getattr(
                                regulation,
                                "source_document",
                                None,
                            )
                        ),
                        "version": (
                            getattr(
                                regulation,
                                "version",
                                None,
                            )
                        ),
                        "metadata": json_safe(
                            getattr(
                                regulation,
                                "metadata",
                                {},
                            )
                            or {}
                        ),
                    }
                )

        else:
            print(
                "WARNING: RegulationModel could not be imported."
            )

        return regulation_rows, rule_rows

    finally:
        session.close()


# ============================================================
# BUILD INDEXES
# ============================================================

def build_indexes(
    regulations: list[dict[str, Any]],
):
    by_id = {}

    by_number = defaultdict(list)

    by_title = defaultdict(list)

    for regulation in regulations:

        rid = normalize(
            regulation.get("id")
        )

        number = normalize_regulation_number(
            regulation.get("number")
        )

        title = normalize_title(
            regulation.get("title")
        )

        if rid:
            by_id[rid] = regulation

        if number:
            by_number[number].append(
                regulation
            )

        if title:
            by_title[title].append(
                regulation
            )

    return (
        by_id,
        by_number,
        by_title,
    )


# ============================================================
# MATCH CHROMA -> POSTGRES
# ============================================================

def match_record(
    record: dict[str, Any],
    by_id,
    by_number,
    by_title,
):
    chroma_id = normalize(
        record.get("regulation_id")
    )

    number = normalize_regulation_number(
        record.get("regulation_number")
    )

    title = normalize_title(
        record.get("title")
    )

    # --------------------------------------------------------
    # 1. Exact regulation ID
    # --------------------------------------------------------

    if chroma_id:

        postgres = by_id.get(
            chroma_id
        )

        if postgres:

            return {
                "classification": "EXACT_ID_MATCH",
                "confidence": 1.0,
                "postgres_regulation_id": postgres["id"],
                "matched_by": "regulation_id",
                "candidate_count": 1,
                "candidates": [postgres],
            }

    # --------------------------------------------------------
    # 2. Regulation number
    # --------------------------------------------------------

    number_candidates = (
        by_number.get(number, [])
        if number
        else []
    )

    if len(number_candidates) == 1:

        postgres = number_candidates[0]

        if chroma_id:
            classification = (
                "NUMBER_MATCH_ID_WRONG"
            )
        else:
            classification = (
                "NUMBER_MATCH_MISSING_ID"
            )

        return {
            "classification": classification,
            "confidence": 0.95,
            "postgres_regulation_id": postgres["id"],
            "matched_by": "regulation_number",
            "candidate_count": 1,
            "candidates": number_candidates,
        }

    if len(number_candidates) > 1:

        return {
            "classification": (
                "NUMBER_MATCH_MULTIPLE"
            ),
            "confidence": 0.0,
            "postgres_regulation_id": None,
            "matched_by": "regulation_number",
            "candidate_count": len(
                number_candidates
            ),
            "candidates": number_candidates,
        }

    # --------------------------------------------------------
    # 3. Title
    # --------------------------------------------------------

    title_candidates = (
        by_title.get(title, [])
        if title
        else []
    )

    if len(title_candidates) == 1:

        postgres = title_candidates[0]

        return {
            "classification": "TITLE_MATCH",
            "confidence": 0.75,
            "postgres_regulation_id": postgres["id"],
            "matched_by": "title",
            "candidate_count": 1,
            "candidates": title_candidates,
        }

    if len(title_candidates) > 1:

        return {
            "classification": "TITLE_MATCH_MULTIPLE",
            "confidence": 0.0,
            "postgres_regulation_id": None,
            "matched_by": "title",
            "candidate_count": len(
                title_candidates
            ),
            "candidates": title_candidates,
        }

    # --------------------------------------------------------
    # 4. No match
    # --------------------------------------------------------

    if not chroma_id and not number and not title:

        classification = (
            "NO_IDENTIFYING_METADATA"
        )

    elif not chroma_id:

        classification = (
            "NO_POSTGRES_MATCH_MISSING_ID"
        )

    else:

        classification = (
            "NO_POSTGRES_MATCH"
        )

    return {
        "classification": classification,
        "confidence": 0.0,
        "postgres_regulation_id": None,
        "matched_by": None,
        "candidate_count": 0,
        "candidates": [],
    }


# ============================================================
# RULE COVERAGE
# ============================================================

def build_rule_coverage(
    regulations,
    rules,
):
    rule_counts = Counter()

    enabled_counts = Counter()

    for rule in rules:

        rid = normalize(
            rule.get("regulation_id")
        )

        if not rid:
            continue

        rule_counts[rid] += 1

        if rule.get("enabled"):
            enabled_counts[rid] += 1

    rows = []

    for regulation in regulations:

        rid = normalize(
            regulation.get("id")
        )

        rows.append(
            {
                "regulation_id": regulation.get(
                    "id"
                ),
                "regulation_number": regulation.get(
                    "number"
                ),
                "title": regulation.get(
                    "title"
                ),
                "rule_count": rule_counts.get(
                    rid,
                    0,
                ),
                "enabled_rule_count": (
                    enabled_counts.get(
                        rid,
                        0,
                    )
                ),
            }
        )

    return rows


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    chroma_records,
    postgres_regulations,
    postgres_rules,
    mapping,
):

    counts = Counter(
        item["classification"]
        for item in mapping
    )

    chroma_with_id = sum(
        bool(
            normalize(
                r.get("regulation_id")
            )
        )
        for r in chroma_records
    )

    chroma_with_number = sum(
        bool(
            normalize_regulation_number(
                r.get("regulation_number")
            )
        )
        for r in chroma_records
    )

    postgres_rule_regulation_ids = set(
        normalize(
            r.get("regulation_id")
        )
        for r in postgres_rules
        if r.get("regulation_id")
    )

    postgres_regulation_ids = set(
        normalize(
            r.get("id")
        )
        for r in postgres_regulations
        if r.get("id")
    )

    orphan_rule_regulation_ids = (
        postgres_rule_regulation_ids
        - postgres_regulation_ids
    )

    print()
    print("=" * 80)
    print("MAPPING SUMMARY")
    print("=" * 80)

    print(
        f"Chroma records                 : "
        f"{len(chroma_records)}"
    )

    print(
        f"Chroma records with ID         : "
        f"{chroma_with_id}"
    )

    print(
        f"Chroma records with number     : "
        f"{chroma_with_number}"
    )

    print(
        f"PostgreSQL regulations         : "
        f"{len(postgres_regulations)}"
    )

    print(
        f"PostgreSQL rules               : "
        f"{len(postgres_rules)}"
    )

    print()
    print("CLASSIFICATION")
    print("-" * 80)

    for key, value in counts.most_common():
        print(
            f"{key:40} {value}"
        )

    print()
    print(
        "PostgreSQL rule regulation IDs "
        "without matching regulation row:",
        len(
            orphan_rule_regulation_ids
        ),
    )

    if orphan_rule_regulation_ids:

        print()

        for rid in sorted(
            orphan_rule_regulation_ids
        ):
            print(
                "  ORPHAN RULE regulation_id:",
                rid,
            )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    filename: str,
    data: Any,
):

    path = OUTPUT_DIR / filename

    with path.open(
        "w",
        encoding="utf-8",
    ) as fh:

        json.dump(
            json_safe(data),
            fh,
            indent=2,
            ensure_ascii=False,
        )

    return path


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 80)
    print("UDCPR REGULATION / CHROMA / POSTGRES AUDIT")
    print("=" * 80)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    chroma_records = load_chroma()

    (
        postgres_regulations,
        postgres_rules,
    ) = load_postgres()

    # --------------------------------------------------------
    # Index
    # --------------------------------------------------------

    (
        by_id,
        by_number,
        by_title,
    ) = build_indexes(
        postgres_regulations
    )

    # --------------------------------------------------------
    # Match
    # --------------------------------------------------------

    mapping = []

    for record in chroma_records:

        result = match_record(
            record,
            by_id,
            by_number,
            by_title,
        )

        mapping.append(
            {
                "chroma_id": record.get(
                    "chroma_id"
                ),
                "chroma_regulation_id": record.get(
                    "regulation_id"
                ),
                "chroma_regulation_number": record.get(
                    "regulation_number"
                ),
                "chroma_title": record.get(
                    "title"
                ),
                "chroma_start_page": record.get(
                    "start_page"
                ),
                "chroma_end_page": record.get(
                    "end_page"
                ),
                **result,
            }
        )

    # --------------------------------------------------------
    # Rule coverage
    # --------------------------------------------------------

    rule_coverage = build_rule_coverage(
        postgres_regulations,
        postgres_rules,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print_summary(
        chroma_records,
        postgres_regulations,
        postgres_rules,
        mapping,
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    files = []

    files.append(
        save_json(
            "chroma_records.json",
            chroma_records,
        )
    )

    files.append(
        save_json(
            "postgres_regulations.json",
            postgres_regulations,
        )
    )

    files.append(
        save_json(
            "postgres_rules.json",
            postgres_rules,
        )
    )

    files.append(
        save_json(
            "mapping_report.json",
            mapping,
        )
    )

    files.append(
        save_json(
            "rule_coverage.json",
            rule_coverage,
        )
    )

    # --------------------------------------------------------
    # Human-readable report
    # --------------------------------------------------------

    counts = Counter(
        item["classification"]
        for item in mapping
    )

    summary_path = (
        OUTPUT_DIR
        / "mapping_summary.txt"
    )

    with summary_path.open(
        "w",
        encoding="utf-8",
    ) as fh:

        fh.write(
            "UDCPR REGULATION MAPPING SUMMARY\n"
        )

        fh.write(
            "=" * 80
            + "\n\n"
        )

        fh.write(
            f"Chroma records: "
            f"{len(chroma_records)}\n"
        )

        fh.write(
            f"PostgreSQL regulations: "
            f"{len(postgres_regulations)}\n"
        )

        fh.write(
            f"PostgreSQL rules: "
            f"{len(postgres_rules)}\n\n"
        )

        for key, value in counts.most_common():

            fh.write(
                f"{key:40} {value}\n"
            )

        fh.write(
            "\n"
        )

        fh.write(
            "HIGH-CONFIDENCE MAPPINGS\n"
        )

        fh.write(
            "-" * 80
            + "\n"
        )

        for item in mapping:

            if item["classification"] in (
                "NUMBER_MATCH_ID_WRONG",
                "NUMBER_MATCH_MISSING_ID",
            ):

                fh.write(
                    f"Chroma ID      : "
                    f"{item['chroma_id']}\n"
                )

                fh.write(
                    f"Chroma number  : "
                    f"{item['chroma_regulation_number']}\n"
                )

                fh.write(
                    f"Current ID     : "
                    f"{item['chroma_regulation_id']}\n"
                )

                fh.write(
                    f"Postgres ID    : "
                    f"{item['postgres_regulation_id']}\n"
                )

                fh.write(
                    f"Classification : "
                    f"{item['classification']}\n"
                )

                fh.write(
                    "\n"
                )

    print()
    print("=" * 80)
    print("OUTPUT")
    print("=" * 80)

    for path in files:
        print(path)

    print(summary_path)

    print()
    print(
        "NO DATABASE RECORDS WERE MODIFIED."
    )

    print()


if __name__ == "__main__":
    main()
