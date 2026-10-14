"""
Abstract base class for OCR providers.

Every OCR engine (Surya, PaddleOCR, Tesseract, Azure, etc.)
must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from townplanning.modules.regulations.ocr.domain.ocr_block import OCRBlock


class OCRProvider(ABC):
    """
    Base interface for OCR providers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Name of OCR engine.
        Example:
            surya
            paddle
            tesseract
        """
        raise NotImplementedError

    @abstractmethod
    def initialize(self) -> None:
        """
        Load OCR model(s).

        Called once during application startup.
        """
        raise NotImplementedError

    @abstractmethod
    def extract(
        self,
        image: Image.Image,
        page: int,
    ) -> list[OCRBlock]:
        """
        Perform OCR on a page image.

        Parameters
        ----------
        image:
            PIL Image

        page:
            Page number (1-based)

        Returns
        -------
        list[OCRBlock]
        """
        raise NotImplementedError

    @abstractmethod
    def supports_language(
        self,
        language: str,
    ) -> bool:
        """
        Returns True if provider supports
        requested language.

        Example:
            mr
            en
            hi
            ta
        """
        raise NotImplementedError

    def shutdown(self) -> None:
        """
        Optional cleanup.

        GPU providers can release memory here.
        """
        pass