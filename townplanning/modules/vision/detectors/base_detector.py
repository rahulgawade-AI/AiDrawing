from __future__ import annotations

from abc import ABC, abstractmethod

from townplanning.modules.vision.domain.drawing import Drawing


class BaseDetector(ABC):
    """
    Base class for all vision detectors.
    """

    @abstractmethod
    def detect(
        self,
        drawing: Drawing,
    ):
        """
        Detect object(s) from drawing.
        """
        raise NotImplementedError