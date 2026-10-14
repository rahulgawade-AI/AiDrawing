from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import chromadb

from townplanning.core.settings import get_settings


OUTPUT = Path("/tmp/chroma_udcpr_audit.json")


REGULATION_PATTERNS = [
    r"Regulation\s+(?:No\.?\s*)?(\d+(?:\.\d+)+)",
    r"Regulation\s+No\.?\s*(\d+(?:\.\d+)+)",
    r"Regulation\s+(\d+(?:\.\d+)+)",
]

TABLE_PATTERNS = [
    r"Table\s+(?:No\.?\s*)?([0-9A-Za-z.\-()]+)",
    r"Table\s+No\.?\s*([0-9A-Za-z.\-()]+)",
]

CHAPTER_PATTERNS = [
    r"Chapter\s+([0-9A-Za-z.\-]+)",
    r"CHAPTER\s+([0-9A-Za-z.\-]+)",
]


TOPICS = {
    "fsi": [
        "FSI",
        "floor space index",
        "floor space",
        "built up area",
        "built-up area",
        "floor area ratio",
    ],
    "setback": [
        "setback",
        "set back",
        "marginal distance",
        "open space",
    ],
    "height": [
        "building height",
        "height of building",
        "maximum height",
        "storey",
        "storeys",
        "floors",
    ],
    "parking": [
        "parking",
        "car parking",
        "two wheeler",
        "two-wheeler",
        "parking space",
    ],
    "staircase": [
        "staircase",
        "stair case",
        "stair",
        "tread",
        "riser",
    ],
    "fire": [
        "fire safety",
        "fire access",
        "fire staircase",
        "fire lift",
        "fire fighting",
        "refuge",
    ],
    "lift": [
        "lift",
        "elevator",
        "lift well",
        "lift lobby",
    ],
    "accessibility": [
        "accessible",
        "accessibility",
        "ramp",
        "barrier free",
    ],
    "amenity": [
        "amenity",
        "amenities",
        "recreational",
        "recreation",
    ],
    "road": [
        "road width",
        "road widening",
        "road",
        "street width",
    ],
    "plot": [
        "plot area",
        "plot size",
        "minimum plot",
        "subdivision",
    ],
}


def extract_matches(patterns, text):
    values = []

    for pattern in patterns:
        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            value = match.group(1).strip()
            if value not in values:
                values.append(value)

    return values


def detect_topics(text):
    text_lower = text.lower()

    result = []

    for topic, keywords in TOPICS.items():

        for keyword in keywords:

            if keyword.lower() in text_lower:
                result.append(topic)
                break

    return result


def main():

    settings = get_settings()

    client = chromadb.PersistentClient(
        path=settings.CHROMA_PATH
    )

    collection = client.get_collection(
        name=settings.CHROMA_COLLECTION
    )

    count = collection.count()

    print("=" * 100)
    print("FULL CHROMA UDCPR AUDIT")
    print("=" * 100)

    print("Path       :", settings.CHROMA_PATH)
    print("Collection :", settings.CHROMA_COLLECTION)
    print("Records    :", count)
    print()

    # Chroma get() can return large collections. Process in batches.
    batch_size = 500

    all_records = []

    metadata_keys = Counter()
    engines = Counter()
    regulation_numbers = Counter()
    tables = Counter()
    chapters = Counter()
    topics = Counter()

    records_with_regulation = 0
    records_with_table = 0
    records_with_topic = 0

    offset = 0

    while offset < count:

        print(
            f"Reading {offset} - "
            f"{min(offset + batch_size, count)} "
            f"of {count}..."
        )

        data = collection.get(
            limit=batch_size,
            offset=offset,
            include=[
                "documents",
                "metadatas",
            ],
        )

        ids = data.get("ids", [])
        documents = data.get("documents", [])
        metadatas = data.get("metadatas", [])

        for index, record_id in enumerate(ids):

            document = (
                documents[index]
                if index < len(documents)
                else ""
            ) or ""

            metadata = (
                metadatas[index]
                if index < len(metadatas)
                else {}
            ) or {}

            for key in metadata:
                metadata_keys[key] += 1

            engine = metadata.get(
                "engine",
                "UNKNOWN",
            )

            engines[str(engine)] += 1

            regulation_ids = extract_matches(
                REGULATION_PATTERNS,
                document,
            )

            table_ids = extract_matches(
                TABLE_PATTERNS,
                document,
            )

            chapter_ids = extract_matches(
                CHAPTER_PATTERNS,
                document,
            )

            detected_topics = detect_topics(
                document,
            )

            for value in regulation_ids:
                regulation_numbers[value] += 1

            for value in table_ids:
                tables[value] += 1

            for value in chapter_ids:
                chapters[value] += 1

            for value in detected_topics:
                topics[value] += 1

            if regulation_ids:
                records_with_regulation += 1

            if table_ids:
                records_with_table += 1

            if detected_topics:
                records_with_topic += 1

            all_records.append(
                {
                    "id": record_id,
                    "metadata": metadata,
                    "regulation_numbers": regulation_ids,
                    "table_numbers": table_ids,
                    "chapter_numbers": chapter_ids,
                    "topics": detected_topics,
                    "document_preview": document[:2000],
                }
            )

        offset += len(ids)

        if not ids:
            break

    audit = {
        "chroma": {
            "path": settings.CHROMA_PATH,
            "collection": settings.CHROMA_COLLECTION,
            "record_count": count,
        },
        "statistics": {
            "records_with_regulation_number":
                records_with_regulation,
            "records_with_table_number":
                records_with_table,
            "records_with_topic":
                records_with_topic,
        },
        "metadata_keys": dict(metadata_keys),
        "engines": dict(engines),
        "regulation_numbers": dict(
            regulation_numbers.most_common()
        ),
        "tables": dict(
            tables.most_common()
        ),
        "chapters": dict(
            chapters.most_common()
        ),
        "topics": dict(
            topics.most_common()
        ),
        "records": all_records,
    }

    OUTPUT.write_text(
        json.dumps(
            audit,
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)

    print("Total records:",
          count)

    print(
        "With regulation number:",
        records_with_regulation,
    )

    print(
        "With table number:",
        records_with_table,
    )

    print(
        "With recognized topic:",
        records_with_topic,
    )

    print()
    print("Metadata keys:")

    for key, value in metadata_keys.most_common():
        print(
            f"  {key:30} {value}"
        )

    print()
    print("Topics:")

    for topic, value in topics.most_common():
        print(
            f"  {topic:30} {value}"
        )

    print()
    print("Output:")
    print(OUTPUT)


if __name__ == "__main__":
    main()
