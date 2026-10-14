from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from townplanning.modules.embeddings.domain.embedding_record import (
    EmbeddingRecord,
)
from townplanning.modules.vectordb.domain.search_result import (
    SearchResult,
)
from typing import Any

class BaseVectorRepository(ABC):

    @abstractmethod
    def add(
        self,
        records: list[EmbeddingRecord],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        records: list[EmbeddingRecord],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        ids: list[str],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    def exists(
        self,
        vector_id: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError