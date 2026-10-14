from abc import ABC
from abc import abstractmethod

import numpy as np

from townplanning.modules.vision.domain.text_block import (
    TextBlock,
)


class OCREngine(ABC):

    @abstractmethod
    def extract(
        self,
        image: np.ndarray,
        page: int = 1,
    ) -> list[TextBlock]:
        ...