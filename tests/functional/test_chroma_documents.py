from pprint import pprint

from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)


def main():

    repo = ChromaRepository()

    data = repo.collection.get()

    print("=" * 80)

    print("IDs")
    pprint(data["ids"])

    print()

    print("Documents")
    pprint(data["documents"])

    print()

    print("Metadata")
    pprint(data["metadatas"])

    print("=" * 80)


if __name__ == "__main__":
    main()