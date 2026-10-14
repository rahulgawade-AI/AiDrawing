from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)


def main():

    repo = ChromaRepository()

    print("=" * 60)

    print("Collection :", repo.collection.name)

    print("Vector Count :", repo.count())

    print("=" * 60)


if __name__ == "__main__":
    main()