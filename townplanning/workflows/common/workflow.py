from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class Workflow(ABC):
    """
    Base class for all LangGraph workflows.
    """

    @abstractmethod
    def run(self, *args, **kwargs):
        """
        Execute the workflow.
        """
        raise NotImplementedError