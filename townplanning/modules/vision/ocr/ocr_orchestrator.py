from __future__ import annotations

from pathlib import Path

from townplanning.modules.vision.domain.text_block import TextBlock
from townplanning.modules.vision.ocr.ocr_engine import OCREngine

from townplanning.modules.vision.preprocessing.preprocess_pipeline import (
    PreprocessPipeline,
)

from townplanning.modules.vision.preprocessing.image_loader import (
    ImageLoader,
)


class OCROrchestrator:
    """
    Runs OCR on multiple versions
    of the same engineering drawing.
    """

    def __init__(
        self,
        engine: OCREngine,
    ):

        self.engine = engine

        self.loader = ImageLoader()

        self.pipeline = PreprocessPipeline()

    def process(
        self,
        image_path: str | Path,
    ) -> list[TextBlock]:

        image = self.loader.load(
            image_path,
        )

        processed = self.pipeline.process(
            image,
        )

        return self.engine.extract(
            processed,
        )