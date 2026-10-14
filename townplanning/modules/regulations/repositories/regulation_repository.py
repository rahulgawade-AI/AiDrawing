"""
Repository contract for Regulation persistence.

The repository persists RegulationDocument objects produced by the
PDF ingestion pipeline.
"""

from abc import ABC
from abc import abstractmethod

from townplanning.modules.regulations.ingestion.regulation_document import (
    RegulationDocument,
)


class RegulationRepository(ABC):

    @abstractmethod
    def save(
        self,
        regulation: RegulationDocument,
    ) -> RegulationDocument:
        """
        Create or update a regulation.
        """
        raise NotImplementedError

    @abstractmethod
    def get(
        self,
        regulation_id: str,
    ) -> RegulationDocument | None:
        """
        Get a regulation by ID.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_number(
        self,
        number: str,
    ) -> RegulationDocument | None:
        """
        Get a regulation by regulation number.
        """
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
    ) -> list[RegulationDocument]:
        """
        Return all regulations.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        regulation_id: str,
    ) -> None:
        """
        Delete a regulation.
        """
        raise NotImplementedError