from __future__ import annotations

from pathlib import Path

import cv2

from townplanning.modules.vision.domain.drawing import Drawing
from townplanning.modules.vision.domain.page import Page
from townplanning.modules.vision.parsers.document_parser import (
    DocumentParser,
)


class ImageParser(DocumentParser):
    """
    Parses PNG/JPG/TIFF images.
    """

    def parse(
        self,
        file_path: Path,
    ) -> Drawing:

        image = cv2.imread(str(file_path))

        if image is None:
            raise FileNotFoundError(file_path)

        height, width = image.shape[:2]

        page = Page(
            number=1,
            width=width,
            height=height,
        )

        drawing = Drawing(
            filename=file_path.name,
            pages=[page],
            metadata={
                "type": "image",
                "path": str(file_path),
            },
        )

        return drawing