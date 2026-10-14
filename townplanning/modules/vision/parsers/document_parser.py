from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from townplanning.modules.vision.domain.drawing import Drawing


class DocumentParser(ABC):
    """
    Base class for all document parsers.

    Supported formats:
        - PDF
        - PNG
        - JPEG
        - TIFF
        - DWG (future)
        - DXF (future)
    """

    @abstractmethod
    def parse(
        self,
        file_path: Path,
    ) -> Drawing:
        """
        Parse a document and return a Drawing object.
        """
        raise NotImplementedError