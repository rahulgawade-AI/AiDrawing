from __future__ import annotations

from typing import Any

import chromadb
import json
from datetime import date, datetime
from uuid import UUID
from townplanning.core.settings import get_settings
from townplanning.modules.embeddings.domain.embedding_record import (
    EmbeddingRecord,
)
from townplanning.modules.vectordb.domain.search_result import (
    SearchResult,
)
from townplanning.modules.vectordb.repositories.base_repository import (
    BaseVectorRepository,
)


class ChromaRepository(BaseVectorRepository):
    """
    ChromaDB repository implementation.
    """

    def __init__(self) -> None:

        settings = get_settings()

        self.collection_name = settings.CHROMA_COLLECTION

        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
        )

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
        )


    def _sanitize_metadata(
        self,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:

        clean = {}

        for key, value in metadata.items():

            if value is None:
                continue

            elif isinstance(value, (str, int, float, bool)):
                clean[key] = value

            elif isinstance(value, UUID):
                clean[key] = str(value)

            elif isinstance(value, (date, datetime)):
                clean[key] = value.isoformat()

            elif isinstance(value, list):
                clean[key] = ", ".join(map(str, value))

            elif isinstance(value, dict):
                clean[key] = json.dumps(value, ensure_ascii=False)

            else:
                clean[key] = str(value)

        return clean

    
    def add(
        self,
        records: list[EmbeddingRecord],
    ) -> None:

        if not records:
            return

        for record in records:
            print("\n====================")
            print(record.id)

            for k, v in record.metadata.items():
                print(
                    f"{k:<25} {type(v).__name__:<20} {repr(v)[:120]}"
                )

        self.collection.add(
            ids=[r.id for r in records],
            documents=[r.text for r in records],
            embeddings=[r.embedding for r in records],
            metadatas=[
    self._sanitize_metadata(r.metadata)
    for r in records
],
        )

    def update(
        self,
        records: list[EmbeddingRecord],
    ) -> None:

        if not records:
            return

        # Chroma supports upsert
        self.collection.upsert(
            ids=[r.id for r in records],
            documents=[r.text for r in records],
            embeddings=[r.embedding for r in records],
            metadatas=[
    self._sanitize_metadata(r.metadata)
    for r in records
],
        )

    def delete(
        self,
        ids: list[str],
    ) -> None:

        if ids:
            self.collection.delete(ids=ids)


    def exists(
        self,
        vector_id: str,
    ) -> bool:

        result = self.collection.get(ids=[vector_id])

        return len(result["ids"]) > 0

    def count(self) -> int:

        return self.collection.count()

    def clear(self) -> None:

        self.client.delete_collection(self.collection_name)

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
        )


    def search(
    self,
    embedding: list[float],
    top_k: int = 10,
        ) -> list[SearchResult]:
        """
        Perform semantic similarity search.
    
        Args:
            embedding: Query embedding.
            top_k: Number of results.
    
        Returns:
            Ranked SearchResult list.
        """
    
        response = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )
    
        ids = response["ids"][0]
        docs = response["documents"][0]
        metadatas = response["metadatas"][0]
        distances = response["distances"][0]
    
        results: list[SearchResult] = []
    
        for doc_id, doc, metadata, distance in zip(
            ids,
            docs,
            metadatas,
            distances,
        ):
            results.append(
                SearchResult(
                    id=doc_id,
                    score=1.0 - float(distance),
                    text=doc,
                    metadata=metadata or {},
                )
            )
    
        return results