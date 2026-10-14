from townplanning.modules.vectordb.repositories.chroma_repository import (
    ChromaRepository,
)

repo = ChromaRepository()

data = repo.collection.get(
    include=["embeddings"]
)

print(len(data["embeddings"][0]))