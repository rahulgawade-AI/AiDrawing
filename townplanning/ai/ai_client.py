"""
Abstract AI client.
"""

from abc import ABC
from abc import abstractmethod

from .models import AIRequest
from .models import AIResponse


class AIClient(ABC):

    @abstractmethod
    def generate(
        self,
        request: AIRequest,
    ) -> AIResponse:
        ...