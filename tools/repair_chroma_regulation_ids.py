#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import chromadb

from townplanning.core.settings import get_settings
from townplanning.infrastructure.database.models.regulation_model import (
    RegulationModel,
)
from townplanning.infrastructure.database.session import SessionLocal


def normalize_number(value):
    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("–", "-")
        .replace("—", "-")
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually update Chroma. Default is dry-run.",
    )

    args = parser.parse_args()

    settings = get_settings()

    chroma_path = settings.CHROMA_PATH
    collection_name = settings.CHROMA_COLLECTION

    print("=" * 80)
    print("SAFE CHROMA REGULATION ID REPAIR")
    print("=" * 80)

    print("Chroma path :", chroma_path)
    print("Collection  :", collection_name)
    print(
        "Mode        :",
        "APPLY" if args.apply else "DRY-RUN",
    )

    # ==========================================================
    # POSTGRES
    # ==========================================================

    session = SessionLocal()

    try:

        regulations = (
            session
            .query(RegulationModel)
            .all()
        )

        print(
            "PostgreSQL regulations:",
            len(regulations),
        )

        by_number = defaultdict(list)

        for regulation in regulations:

            number = normalize_number(
                getattr(
                    regulation,
                    "number",
                    None,
                )
            )

            if not number:
                continue

            by_number[number].append(
                {
                    "id": str(regulation.id),
                    "number": getattr(
                        regulation,
                        "number",
                        None,
                    ),
                    "title": getattr(
                        regulation,
                        "title",
                        None,
                    ),
                    "page_start": getattr(
                        regulation,
                        "page_start",
                        None,
                    ),
                    "page_end": getattr(
                        regulation,
                        "page_end",
                        None,
                    ),
                }
            )

        # ======================================================
        # CHROMA
        # ======================================================

        client = chromadb.PersistentClient(
            path=chroma_path
        )

        collection = client.get_collection(
            name=collection_name
        )

        total = collection.count()

        print(
            "Chroma records:",
            total,
        )

        result = collection.get(
            limit=total,
            include=[
                "metadatas",
                "documents",
            ],
        )

        ids = result.get("ids") or []
        metadatas = result.get("metadatas") or []
        documents = result.get("documents") or []

        updates = []

        stats = {
            "total": total,
            "already_has_id": 0,
            "missing_number": 0,
            "unique_number": 0,
            "ambiguous_number": 0,
            "unknown_number": 0,
            "updates": 0,
        }

        # ======================================================
        # ANALYZE
        # ======================================================

        for index, chroma_id in enumerate(ids):

            metadata = (
                metadatas[index]
                if index < len(metadatas)
                else {}
            )

            metadata = dict(metadata or {})

            document = (
                documents[index]
                if index < len(documents)
                else ""
            )

            existing_id = metadata.get(
                "regulation_id"
            )

            if existing_id:
                stats["already_has_id"] += 1
                continue

            number = normalize_number(
                metadata.get(
                    "regulation_number"
                )
            )

            if not number:
                stats["missing_number"] += 1
                continue

            candidates = by_number.get(
                number,
                []
            )

            if len(candidates) == 0:

                stats["unknown_number"] += 1
                continue

            if len(candidates) > 1:

                stats["ambiguous_number"] += 1
                continue

            # --------------------------------------------------
            # EXACTLY ONE PostgreSQL regulation for this number
            # --------------------------------------------------

            candidate = candidates[0]

            new_metadata = dict(metadata)

            new_metadata[
                "regulation_id"
            ] = candidate["id"]

            # Preserve existing values.
            #
            # Add useful authoritative metadata only if absent.
            if not new_metadata.get(
                "regulation_number"
            ):
                new_metadata[
                    "regulation_number"
                ] = candidate["number"]

            update = {
                "chroma_id": chroma_id,
                "regulation_number": (
                    metadata.get(
                        "regulation_number"
                    )
                ),
                "postgres_regulation_id": (
                    candidate["id"]
                ),
                "postgres_title": (
                    candidate["title"]
                ),
                "start_page": (
                    metadata.get(
                        "start_page"
                    )
                ),
                "end_page": (
                    metadata.get(
                        "end_page"
                    )
                ),
                "document_preview": (
                    document or ""
                )[:250],
                "metadata": new_metadata,
            }

            updates.append(update)

        stats["updates"] = len(updates)

        # ======================================================
        # REPORT
        # ======================================================

        print()
        print("=" * 80)
        print("ANALYSIS")
        print("=" * 80)

        for key, value in stats.items():

            print(
                f"{key:25}: {value}"
            )

        print()
        print(
            "Records that WILL be changed:",
            len(updates),
        )

        # ======================================================
        # SAVE PROPOSED UPDATE
        # ======================================================

        audit_dir = Path(
            "/tmp/chroma_regulation_repair"
        )

        audit_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        proposal_path = (
            audit_dir
            / f"repair_proposal_{timestamp}.json"
        )

        with proposal_path.open(
            "w",
            encoding="utf-8",
        ) as fh:

            json.dump(
                {
                    "stats": stats,
                    "updates": updates,
                },
                fh,
                indent=2,
                ensure_ascii=False,
            )

        print()
        print(
            "Proposal:",
            proposal_path,
        )

        # ======================================================
        # DRY RUN
        # ======================================================

        if not args.apply:

            print()
            print("=" * 80)
            print("DRY-RUN COMPLETE")
            print("=" * 80)

            print(
                "No Chroma records were modified."
            )

            print(
                "Run again with --apply to perform "
                "the update."
            )

            return

        # ======================================================
        # APPLY
        # ======================================================

        print()
        print("=" * 80)
        print("APPLYING UPDATES")
        print("=" * 80)

        batch_size = 100

        for start in range(
            0,
            len(updates),
            batch_size,
        ):

            batch = updates[
                start:start + batch_size
            ]

            collection.update(
                ids=[
                    item["chroma_id"]
                    for item in batch
                ],
                metadatas=[
                    item["metadata"]
                    for item in batch
                ],
            )

            print(
                f"Updated "
                f"{min(start + batch_size, len(updates))}"
                f"/{len(updates)}"
            )

        print()
        print("=" * 80)
        print("REPAIR COMPLETE")
        print("=" * 80)

        print(
            "Updated records:",
            len(updates),
        )

        print(
            "PostgreSQL records modified: 0"
        )

    finally:

        session.close()


if __name__ == "__main__":
    main()
