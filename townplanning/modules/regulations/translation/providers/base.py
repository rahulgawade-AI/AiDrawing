from abc import ABC, abstractmethod


class TranslationProvider(ABC):

    @abstractmethod
    def translate(self, text: str) -> str:
        """Translate text to English."""
        pass