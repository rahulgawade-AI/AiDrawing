from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from townplanning.modules.query.dom.query import Query


class BaseQueryProvider(ABC):
    """
    Base class for query providers.
    """

    @abstractmethod
    def process(
        self,
        question: str,
    ) -> Query:
        """
        Process a user question into a normalized Query.
        """
        raise NotImplementedError