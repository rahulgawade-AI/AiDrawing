from abc import ABC
from abc import abstractmethod


class BaseWorkflow(ABC):

    @abstractmethod
    def execute(self, *args, **kwargs):
        """Execute the workflow."""
        raise NotImplementedError