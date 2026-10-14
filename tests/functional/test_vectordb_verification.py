from collections import Counter

from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)


def main() -> None:

    repo = ChromaRepository()

    print("=" * 80)
    print("VECTOR DATABASE VERIFICATION")
    print("=" * 80)

    total = repo.count()

    print(f"\nTotal vectors : {total}")

    source_types = [
        "OCR",
        "REGULATION",
        "RULE",
        "TABLE",
        "KNOWLEDGE_CARD",
    ]

    print("\nVectors by source type")
    print("-" * 80)

    for source_type in source_types:

        result = repo.collection.get(
            where={"source_type": source_type},
        )

        count = len(result["ids"])

        print(f"{source_type:<20} {count}")

    print("\nSample document from each source")
    print("-" * 80)

    for source_type in source_types:

        result = repo.collection.get(
            where={"source_type": source_type},
            limit=1,
        )

        if not result["ids"]:
            print(f"{source_type:<20} NOT FOUND")
            continue

        print(f"\n[{source_type}]")
        print("ID:", result["ids"][0])
        print("Metadata:", result["metadatas"][0])
        print("Document:")
        print(result["documents"][0][:400])
        print("-" * 80)


if __name__ == "__main__":
    main()