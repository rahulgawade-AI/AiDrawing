from __future__ import annotations

from abc import ABC, abstractmethod

from townplanning.modules.regulations.ocr.domain.ocr_record import OCRRecord


class OCRRepository(ABC):

    @abstractmethod
    def save(
        self,
        record: OCRRecord,
    ) -> None:
        raise NotImplementedError