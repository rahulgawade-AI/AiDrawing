#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base

from townplanning.infrastructure.database.engine import engine
from townplanning.infrastructure.database.session import SessionLocal


# =============================================================================
# CONFIG
# =============================================================================

BASE_DIR = Path("/home/ubuntu/llmproject/ai-town-planning")

TRANSLATION_DIR = (
    BASE_DIR / "data/regulations/regional_translation"
)

ASSOCIATION_REPORT = Path(
    "/tmp/udcpr_regional_associations_v2.json"
)

CHROMA_PATH = (
    BASE_DIR / "data/chroma"
)

COLLECTION_NAME = "townplanning"

SOURCE_DOCUMENT = "UDCPR.pdf"

Base = declarative_base()


# =============================================================================
# POSTGRESQL TABLE
# =============================================================================

class RegionalDocument(Base):

    __tablename__ = "regional_documents"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    document_id = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    pdf_page_start = Column(
        Integer,
        nullable=False,
    )

    pdf_page_end = Column(
        Integer,
        nullable=False,
    )

    document_type = Column(
        String(100),
        nullable=False,
    )

    association_status = Column(
        String(100),
        nullable=False,
    )

    associated_regulations = Column(
        JSON,
        nullable=False,
        default=list,
    )

    primary_regulations = Column(
        JSON,
        nullable=False,
        default=list,
    )

    secondary_regulations = Column(
        JSON,
        nullable=False,
        default=list,
    )

    procedural_regulations = Column(
        JSON,
        nullable=False,
        default=list,
    )

    source_document = Column(
        String(255),
        nullable=False,
    )

    source_ocr_text = Column(
        Text,
        nullable=False,
    )

    translated_english_text = Column(
        Text,
        nullable=False,
    )

    source_ocr_file = Column(
        Text,
        nullable=True,
    )

    translation_engine = Column(
        String(100),
        nullable=True,
    )

    translation_model = Column(
        String(255),
        nullable=True,
    )

    content_sha256 = Column(
        String(64),
        nullable=False,
        index=True,
    )

    metadata_json = Column(
        JSON,
        nullable=False,
        default=dict,
    )

    enabled = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


# =============================================================================
# HELPERS
# =============================================================================

def sha256_text(text: str) -> str:

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def normalize_pages(value: Any) -> list[int]:

    if value is None:
        return []

    if isinstance(value, int):
        return [value]

    if isinstance(value, list):

        result = []

        for item in value:

            try:
                result.append(int(item))
            except (TypeError, ValueError):
                pass

        return sorted(set(result))

    if isinstance(value, str):

        result = []

        for part in value.replace(
            ",",
            " ",
        ).split():

            try:
                result.append(int(part))
            except ValueError:
                pass

        return sorted(set(result))

    return []


def get_translation_page(
    data: dict[str, Any],
    path: Path,
) -> int | None:

    page = data.get("pdf_page")

    if page is not None:

        try:
            return int(page)
        except (TypeError, ValueError):
            pass

    digits = "".join(
        c for c in path.stem
        if c.isdigit()
    )

    if digits:

        try:
            return int(digits)
        except ValueError:
            pass

    return None


def get_translation_text(
    data: dict[str, Any],
) -> tuple[str, str]:

    original = (
        data.get("original_ocr_text")
        or data.get("source_ocr_text")
        or data.get("ocr_text")
        or ""
    )

    translated = (
        data.get("translated_english_text")
        or data.get("translated_text")
        or data.get("translation")
        or ""
    )

    return (
        str(original).strip(),
        str(translated).strip(),
    )


# =============================================================================
# TRANSLATIONS
# =============================================================================

def load_translations():

    translations = {}

    for path in sorted(
        TRANSLATION_DIR.glob("page_*.json")
    ):

        try:

            data = load_json(path)

        except Exception as exc:

            print(
                f"WARNING: Cannot read {path}: {exc}",
                file=sys.stderr,
            )

            continue

        page = get_translation_page(
            data,
            path,
        )

        if page is None:
            continue

        original, translated = (
            get_translation_text(data)
        )

        if not translated:

            print(
                f"WARNING: Empty translation: "
                f"{path}"
            )

            continue

        translations[page] = {
            "path": path,
            "data": data,
            "original": original,
            "translated": translated,
        }

    return translations


# =============================================================================
# ASSOCIATION REPORT
# =============================================================================

def load_association_groups():

    if not ASSOCIATION_REPORT.exists():

        print(
            "WARNING: Association report does not exist:"
        )

        print(
            ASSOCIATION_REPORT
        )

        return []

    report = load_json(
        ASSOCIATION_REPORT
    )

    groups = (
        report.get("association_groups")
        or report.get("groups")
        or report.get("documents")
        or []
    )

    if isinstance(groups, dict):
        groups = list(groups.values())

    result = []

    for group in groups:

        if not isinstance(
            group,
            dict,
        ):
            continue

        pages = normalize_pages(
            group.get("pages")
        )

        if not pages:

            start = group.get(
                "page_start"
            )

            end = group.get(
                "page_end"
            )

            if start is not None:

                try:

                    start = int(start)

                    end = int(
                        end
                        if end is not None
                        else start
                    )

                    pages = list(
                        range(
                            start,
                            end + 1,
                        )
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    pages = []

        if not pages:
            continue

        regulations = (
            group.get(
                "associated_regulations"
            )
            or group.get(
                "udcpr_regulations"
            )
            or group.get(
                "regulations"
            )
            or []
        )

        if isinstance(
            regulations,
            str,
        ):
            regulations = [
                regulations
            ]

        result.append(
            {
                "pages": sorted(
                    set(pages)
                ),
                "association_status": (
                    group.get(
                        "association_status"
                    )
                    or group.get(
                        "status"
                    )
                    or (
                        "associated"
                        if regulations
                        else "standalone"
                    )
                ),
                "associated_regulations": list(
                    regulations
                ),
                "primary_regulations": list(
                    group.get(
                        "primary_regulations"
                    )
                    or []
                ),
                "secondary_regulations": list(
                    group.get(
                        "secondary_regulations"
                    )
                    or []
                ),
                "procedural_regulations": list(
                    group.get(
                        "procedural_regulations"
                    )
                    or []
                ),
                "document_type": (
                    group.get(
                        "document_type"
                    )
                    or "regional_government_explanation"
                ),
            }
        )

    return result


# =============================================================================
# FALLBACK
# =============================================================================

def add_unassociated_pages(
    groups,
    translations,
):

    used_pages = set()

    for group in groups:

        used_pages.update(
            group["pages"]
        )

    for page in sorted(
        translations
    ):

        if page in used_pages:
            continue

        groups.append(
            {
                "pages": [page],
                "association_status": "standalone",
                "associated_regulations": [],
                "primary_regulations": [],
                "secondary_regulations": [],
                "procedural_regulations": [],
                "document_type": (
                    "regional_government_explanation"
                ),
            }
        )

    return groups


# =============================================================================
# BUILD DOCUMENTS
# =============================================================================

def build_documents(
    groups,
    translations,
):

    documents = []

    for group in groups:

        pages = sorted(
            set(group["pages"])
        )

        entries = []

        missing = []

        for page in pages:

            item = translations.get(page)

            if item is None:

                missing.append(page)

                continue

            entries.append(
                (
                    page,
                    item,
                )
            )

        if not entries:
            continue

        actual_pages = [
            page
            for page, _ in entries
        ]

        page_start = min(
            actual_pages
        )

        page_end = max(
            actual_pages
        )

        original_parts = []
        translated_parts = []
        source_files = []

        engines = set()
        models = set()

        for page, item in entries:

            original_parts.append(
                f"[PDF PAGE {page}]\n"
                f"{item['original']}"
            )

            translated_parts.append(
                f"[PDF PAGE {page}]\n"
                f"{item['translated']}"
            )

            source_files.append(
                str(item["path"])
            )

            data = item["data"]

            if data.get(
                "translation_engine"
            ):
                engines.add(
                    str(
                        data[
                            "translation_engine"
                        ]
                    )
                )

            if data.get(
                "translation_model"
            ):
                models.add(
                    str(
                        data[
                            "translation_model"
                        ]
                    )
                )

        original_text = "\n\n".join(
            original_parts
        ).strip()

        translated_text = "\n\n".join(
            translated_parts
        ).strip()

        document_id = (
            f"regional_{page_start:04d}_"
            f"{page_end:04d}"
        )

        documents.append(
            {
                "document_id": document_id,

                "pdf_page_start": page_start,

                "pdf_page_end": page_end,

                "document_type": group[
                    "document_type"
                ],

                "association_status": group[
                    "association_status"
                ],

                "associated_regulations": group[
                    "associated_regulations"
                ],

                "primary_regulations": group[
                    "primary_regulations"
                ],

                "secondary_regulations": group[
                    "secondary_regulations"
                ],

                "procedural_regulations": group[
                    "procedural_regulations"
                ],

                "source_ocr_text": original_text,

                "translated_english_text": translated_text,

                "source_ocr_file": ";".join(
                    source_files
                ),

                "translation_engine": (
                    ",".join(
                        sorted(engines)
                    )
                    or None
                ),

                "translation_model": (
                    ",".join(
                        sorted(models)
                    )
                    or None
                ),

                "content_sha256": sha256_text(
                    translated_text
                ),

                "metadata_json": {
                    "pages": actual_pages,
                    "reported_pages": pages,
                    "missing_pages": missing,
                    "association": group,
                    "translation_files": source_files,
                },
            }
        )

    return documents


# =============================================================================
# POSTGRESQL
# =============================================================================

def ensure_postgres_table():

    RegionalDocument.__table__.create(
        engine,
        checkfirst=True,
    )


def insert_postgres(
    db,
    document,
):

    existing = (
        db.query(
            RegionalDocument
        )
        .filter(
            RegionalDocument.document_id
            == document["document_id"]
        )
        .one_or_none()
    )

    if existing is not None:

        print(
            f"SKIPPED PostgreSQL: "
            f"{document['document_id']}"
        )

        return False

    row = RegionalDocument(

        document_id=document[
            "document_id"
        ],

        pdf_page_start=document[
            "pdf_page_start"
        ],

        pdf_page_end=document[
            "pdf_page_end"
        ],

        document_type=document[
            "document_type"
        ],

        association_status=document[
            "association_status"
        ],

        associated_regulations=document[
            "associated_regulations"
        ],

        primary_regulations=document[
            "primary_regulations"
        ],

        secondary_regulations=document[
            "secondary_regulations"
        ],

        procedural_regulations=document[
            "procedural_regulations"
        ],

        source_document=SOURCE_DOCUMENT,

        source_ocr_text=document[
            "source_ocr_text"
        ],

        translated_english_text=document[
            "translated_english_text"
        ],

        source_ocr_file=document[
            "source_ocr_file"
        ],

        translation_engine=document[
            "translation_engine"
        ],

        translation_model=document[
            "translation_model"
        ],

        content_sha256=document[
            "content_sha256"
        ],

        metadata_json=document[
            "metadata_json"
        ],

        enabled=True,
    )

    db.add(row)
    db.commit()

    print(
        f"INSERTED PostgreSQL: "
        f"{document['document_id']}"
    )

    return True


# =============================================================================
# EMBEDDING SERVICE
# =============================================================================

def get_embedding_service():

    from townplanning.modules.embeddings.providers.provider_factory import (
        ProviderFactory,
    )

    from townplanning.modules.embeddings.services.embedding_service import (
        EmbeddingService,
    )

    provider = ProviderFactory.create()

    return EmbeddingService(
        provider
    )


def generate_embeddings(
    embedding_service,
    texts,
    ids,
):
    """
    Generate embeddings using the project's existing
    EmbeddingService.embed_chunks() API.

    The existing Chroma collection is 768-dimensional.
    Refuse any embedding with a different dimension.
    """

    from townplanning.modules.embeddings.domain.embedding_request import (
        EmbeddingRequest,
    )

    if len(texts) != len(ids):
        raise RuntimeError(
            f"text/id count mismatch: "
            f"{len(texts)} texts vs {len(ids)} ids"
        )

    requests = []

    for request_id, text in zip(ids, texts):
        requests.append(
            EmbeddingRequest(
                id=str(request_id),
                text=text,
                metadata={
                    "source": "udcpr_regional",
                    "document_id": str(request_id),
                },
            )
        )

    print(
        f"Generating embeddings for "
        f"{len(requests)} document(s)..."
    )

    results = embedding_service.embed_chunks(
        requests
    )

    if results is None:
        raise RuntimeError(
            "EmbeddingService.embed_chunks() "
            "returned None."
        )

    embeddings = []

    for result in results:

        vector = None

        if hasattr(result, "embedding"):
            vector = result.embedding

        elif hasattr(result, "vector"):
            vector = result.vector

        elif hasattr(result, "values"):
            vector = result.values

        elif isinstance(result, dict):
            vector = (
                result.get("embedding")
                or result.get("vector")
                or result.get("values")
            )

        if vector is None:
            raise RuntimeError(
                "Could not extract embedding vector "
                f"from result type: {type(result)}"
            )

        vector = list(vector)

        print(
            f"Generated embedding dimension: "
            f"{len(vector)}"
        )

        if len(vector) != 768:
            raise RuntimeError(
                "EMBEDDING DIMENSION MISMATCH: "
                f"generated {len(vector)}, "
                "expected 768. "
                "NO CHROMA INSERT WILL BE PERFORMED."
            )

        embeddings.append(vector)

    if len(embeddings) != len(texts):
        raise RuntimeError(
            "Embedding result count mismatch: "
            f"expected {len(texts)}, "
            f"got {len(embeddings)}"
        )

    return embeddings


# =============================================================================
# CHROMA
# =============================================================================

def get_collection():

    client = chromadb.PersistentClient(
        path=str(
            CHROMA_PATH
        )
    )

    try:

        collection = client.get_collection(
            name=COLLECTION_NAME
        )

    except Exception as exc:

        raise RuntimeError(
            f"Chroma collection "
            f"'{COLLECTION_NAME}' does not exist. "
            f"Refusing to create another collection.\n"
            f"{exc}"
        )

    return client, collection


def chroma_id_exists(
    collection,
    document_id,
):

    result = collection.get(
        ids=[document_id]
    )

    return document_id in (
        result.get("ids") or []
    )


def count_regional(
    collection,
):

    data = collection.get(
        include=["metadatas"]
    )

    count = 0

    for metadata in (
        data.get("metadatas") or []
    ):

        if not metadata:
            continue

        if metadata.get(
            "source_type"
        ) == "regional_government":

            count += 1

    return count


def insert_chroma(
    collection,
    documents,
    embedding_service,
):

    inserted = 0
    skipped = 0

    for document in documents:

        document_id = document[
            "document_id"
        ]

        # -------------------------------------------------------------
        # Existing ID check
        # -------------------------------------------------------------

        if chroma_id_exists(
            collection,
            document_id,
        ):

            print(
                f"SKIPPED Chroma: "
                f"{document_id}"
            )

            skipped += 1

            continue

        translated = document[
            "translated_english_text"
        ].strip()

        original = document[
            "source_ocr_text"
        ].strip()

        chroma_document = (
            translated
            + "\n\n"
            + "[ORIGINAL_OCR]\n"
            + original
            + "\n[/ORIGINAL_OCR]"
        )

        metadata = {

            "source_type":
                "regional_government",

            "document_type":
                document[
                    "document_type"
                ],

            "association_status":
                document[
                    "association_status"
                ],

            "pdf_page_start":
                document[
                    "pdf_page_start"
                ],

            "pdf_page_end":
                document[
                    "pdf_page_end"
                ],

            "source_document":
                SOURCE_DOCUMENT,

            "source_ocr_file":
                document[
                    "source_ocr_file"
                ],

            "translation_engine":
                document[
                    "translation_engine"
                ] or "",

            "translation_model":
                document[
                    "translation_model"
                ] or "",

            "content_sha256":
                document[
                    "content_sha256"
                ],

            "associated_regulations":
                json.dumps(
                    document[
                        "associated_regulations"
                    ],
                    ensure_ascii=False,
                ),

            "primary_regulations":
                json.dumps(
                    document[
                        "primary_regulations"
                    ],
                    ensure_ascii=False,
                ),

            "secondary_regulations":
                json.dumps(
                    document[
                        "secondary_regulations"
                    ],
                    ensure_ascii=False,
                ),

            "procedural_regulations":
                json.dumps(
                    document[
                        "procedural_regulations"
                    ],
                    ensure_ascii=False,
                ),
        }

        # -------------------------------------------------------------
        # Generate using project's Ollama embedding stack
        # -------------------------------------------------------------

        embeddings = generate_embeddings(
            embedding_service,
            [chroma_document],
            [document_id],
        )

        vector = embeddings[0]

        print(
            f"Embedding dimension: "
            f"{document_id} = {len(vector)}"
        )

        # -------------------------------------------------------------
        # APPEND ONLY
        #
        # NEVER use upsert()
        # NEVER use update()
        # NEVER use delete()
        # -------------------------------------------------------------

        collection.add(
            ids=[document_id],
            documents=[chroma_document],
            metadatas=[metadata],
            embeddings=[vector],
        )

        print(
            f"INSERTED Chroma: "
            f"{document_id}"
        )

        inserted += 1

    return inserted, skipped


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    args = parser.parse_args()

    print("=" * 80)
    print(
        "UDCPR REGIONAL DOCUMENT "
        "APPEND-ONLY LOADER"
    )
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Translation
    # -------------------------------------------------------------------------

    translations = load_translations()

    print()
    print(
        f"Translation pages found: "
        f"{len(translations)}"
    )

    if not translations:

        raise RuntimeError(
            "No regional translation files found."
        )

    # -------------------------------------------------------------------------
    # Associations
    # -------------------------------------------------------------------------

    groups = load_association_groups()

    groups = add_unassociated_pages(
        groups,
        translations,
    )

    print(
        f"Association groups: "
        f"{len(groups)}"
    )

    # -------------------------------------------------------------------------
    # Documents
    # -------------------------------------------------------------------------

    documents = build_documents(
        groups,
        translations,
    )

    print(
        f"Documents to process: "
        f"{len(documents)}"
    )

    # -------------------------------------------------------------------------
    # PostgreSQL
    # -------------------------------------------------------------------------

    print()
    print("=" * 80)
    print("POSTGRESQL INSERT-ONLY")
    print("=" * 80)

    ensure_postgres_table()

    db = SessionLocal()

    pg_inserted = 0
    pg_skipped = 0

    try:

        for document in documents:

            if args.dry_run:

                existing = (
                    db.query(
                        RegionalDocument
                    )
                    .filter(
                        RegionalDocument.document_id
                        == document[
                            "document_id"
                        ]
                    )
                    .one_or_none()
                )

                if existing:

                    print(
                        f"DRY-RUN PostgreSQL SKIP: "
                        f"{document['document_id']}"
                    )

                else:

                    print(
                        f"DRY-RUN PostgreSQL INSERT: "
                        f"{document['document_id']}"
                    )

            else:

                inserted = insert_postgres(
                    db,
                    document,
                )

                if inserted:
                    pg_inserted += 1
                else:
                    pg_skipped += 1

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()

    print()
    print(
        f"PostgreSQL inserted: "
        f"{pg_inserted}"
    )

    print(
        f"PostgreSQL skipped  : "
        f"{pg_skipped}"
    )

    # -------------------------------------------------------------------------
    # Chroma
    # -------------------------------------------------------------------------

    print()
    print("=" * 80)
    print("CHROMADB INSERT-ONLY")
    print("=" * 80)

    _, collection = get_collection()

    before_total = collection.count()

    before_regional = count_regional(
        collection
    )

    print(
        f"Chroma records before: "
        f"{before_total}"
    )

    print(
        f"Non-regional records: "
        f"{before_total - before_regional}"
    )

    print(
        f"Existing regional records: "
        f"{before_regional}"
    )

    # -------------------------------------------------------------------------
    # SAFETY
    # -------------------------------------------------------------------------

    if before_total < 329:

        raise RuntimeError(
            "SAFETY STOP: Chroma contains fewer "
            f"than 329 records ({before_total}). "
            "Refusing to modify collection."
        )

    if args.dry_run:

        print()
        print(
            "DRY-RUN: Chroma writes skipped."
        )

        for document in documents:

            print(
                f"WOULD INSERT Chroma: "
                f"{document['document_id']}"
            )

        return 0

    # -------------------------------------------------------------------------
    # Embedding service
    # -------------------------------------------------------------------------

    embedding_service = (
        get_embedding_service()
    )

    # -------------------------------------------------------------------------
    # Insert
    # -------------------------------------------------------------------------

    chroma_inserted, chroma_skipped = (
        insert_chroma(
            collection,
            documents,
            embedding_service,
        )
    )

    # -------------------------------------------------------------------------
    # Final verification
    # -------------------------------------------------------------------------

    after_total = collection.count()

    after_regional = count_regional(
        collection
    )

    print()
    print("=" * 80)
    print("FINAL VERIFICATION")
    print("=" * 80)

    print(
        f"Chroma records before : "
        f"{before_total}"
    )

    print(
        f"Chroma records after  : "
        f"{after_total}"
    )

    print(
        f"Regional before       : "
        f"{before_regional}"
    )

    print(
        f"Regional after        : "
        f"{after_regional}"
    )

    print(
        f"Chroma inserted       : "
        f"{chroma_inserted}"
    )

    print(
        f"Chroma skipped        : "
        f"{chroma_skipped}"
    )

    print(
        f"PostgreSQL inserted   : "
        f"{pg_inserted}"
    )

    print(
        f"PostgreSQL skipped     : "
        f"{pg_skipped}"
    )

    expected_total = (
        before_total
        + chroma_inserted
    )

    if after_total != expected_total:

        raise RuntimeError(
            "FINAL VERIFICATION FAILED: "
            f"expected Chroma total "
            f"{expected_total}, "
            f"got {after_total}"
        )

    expected_regional = (
        before_regional
        + chroma_inserted
    )

    if after_regional != expected_regional:

        raise RuntimeError(
            "FINAL VERIFICATION FAILED: "
            f"expected regional count "
            f"{expected_regional}, "
            f"got {after_regional}"
        )

    print()
    print("=" * 80)
    print("SUCCESS")
    print("=" * 80)

    print(
        "Append-only regional load completed."
    )

    print(
        "Existing canonical Chroma records "
        "were not overwritten."
    )

    print(
        "Existing PostgreSQL records "
        "were not overwritten."
    )

    return 0


if __name__ == "__main__":

    try:

        raise SystemExit(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\nInterrupted.",
            file=sys.stderr,
        )

        raise SystemExit(130)

    except Exception as exc:

        print()
        print("=" * 80)
        print("ERROR")
        print("=" * 80)

        print(
            str(exc)
        )

        raise
