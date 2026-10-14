"""
Knowledge Repository Interface.
"""

from abc import ABC, abstractmethod

from townplanning.modules.regulations.domain import KnowledgeCard


class KnowledgeRepository(ABC):

    @abstractmethod
    def save(
        self,
        knowledge: KnowledgeCard,
    ) -> KnowledgeCard:
        ...

    @abstractmethod
    def get(
        self,
        knowledge_id: str,
    ) -> KnowledgeCard | None:
        ...

    @abstractmethod
    def exists(
        self,
        knowledge_id: str,
    ) -> bool:
        ...

    @abstractmethod
    def delete(
        self,
        knowledge_id: str,
    ) -> None:
        ...