from __future__ import annotations

import tempfile
from pathlib import Path
import os

os.environ.setdefault(
    "FLAGS_enable_pir_api",
    "0",
)
import cv2
import numpy as np
from paddleocr import PaddleOCR

from townplanning.modules.vision.domain.bounding_box import (
    BoundingBox,
)
from townplanning.modules.vision.domain.text_block import (
    TextBlock,
)
from townplanning.modules.vision.ocr.ocr_engine import (
    OCREngine,
)


class PaddleOCREngine(OCREngine):
    """
    PaddleOCR 3.x implementation.

    Accepts:
        - image path
        - NumPy/OpenCV image

    NumPy images are temporarily written to disk because
    PaddleOCR 3.x expects a supported image/PDF input source.
    """

    def __init__(self):

        self._ocr = PaddleOCR(
            lang="en",

            use_doc_orientation_classify=False,

            use_doc_unwarping=False,

            use_textline_orientation=False,

            enable_mkldnn=False,
        )

    def extract(
        self,
        image: str | Path | np.ndarray,
        page: int = 1,
    ) -> list[TextBlock]:

        temporary_file = None

        try:

            #
            # Existing image path
            #
            if isinstance(image, (str, Path)):

                input_source = str(image)

            #
            # NumPy/OpenCV image
            #
            elif isinstance(image, np.ndarray):

                temporary_file = tempfile.NamedTemporaryFile(
                    suffix=".png",
                    delete=False,
                )

                temporary_file.close()

                input_source = temporary_file.name

                success = cv2.imwrite(
                    input_source,
                    image,
                )

                if not success:
                    raise RuntimeError(
                        "Unable to write temporary image "
                        "for PaddleOCR."
                    )

            else:

                raise TypeError(
                    "PaddleOCREngine expects either "
                    "a file path or numpy.ndarray. "
                    f"Received: {type(image)}"
                )

            #
            # PaddleOCR 3.x
            #
            result = self._ocr.predict(
                input_source,
            )

            return self._parse_result(
                result,
                page,
            )

        finally:

            #
            # Remove temporary image
            #
            if temporary_file is not None:

                try:
                    Path(
                        temporary_file.name
                    ).unlink(
                        missing_ok=True
                    )

                except Exception:
                    pass

    def _parse_result(
        self,
        result,
        page: int,
    ) -> list[TextBlock]:

        blocks = []

        if result is None:
            return blocks

        #
        # PaddleOCR 3.x returns an iterable
        # of result objects.
        #
        for item in result:

            if item is None:
                continue

            #
            # PaddleOCR Result object
            #
            if hasattr(item, "json"):

                data = item.json

                if callable(data):
                    data = data()

            #
            # Dictionary result
            #
            elif isinstance(item, dict):

                data = item

            else:

                continue

            #
            # Some PaddleOCR versions return
            # a JSON string.
            #
            if isinstance(data, str):

                import json

                data = json.loads(data)

            if not isinstance(data, dict):
                continue

            data = data.get(
                "res",
                data,
            )

            texts = data.get(
                "rec_texts",
                [],
            )

            scores = data.get(
                "rec_scores",
                [],
            )

            boxes = data.get(
                "rec_boxes",
                [],
            )

            for text, confidence, box in zip(
                texts,
                scores,
                boxes,
            ):

                if not text:
                    continue

                if box is None:
                    continue

                box = np.asarray(
                    box,
                    dtype=float,
                )

                #
                # PaddleOCR rec_boxes normally:
                #
                # [x1, y1, x2, y2]
                #
                if box.size == 4:

                    x1, y1, x2, y2 = box.tolist()

                #
                # Polygon:
                #
                # [[x1,y1], [x2,y2], ...]
                #
                elif box.ndim == 2:

                    xs = box[:, 0]

                    ys = box[:, 1]

                    x1 = float(xs.min())

                    y1 = float(ys.min())

                    x2 = float(xs.max())

                    y2 = float(ys.max())

                else:

                    continue

                blocks.append(
                    TextBlock(
                        text=str(text),
                        confidence=float(
                            confidence
                        ),
                        page=page,
                        bounding_box=BoundingBox(
                            min_x=x1,
                            min_y=y1,
                            max_x=x2,
                            max_y=y2,
                        ),
                    )
                )

        return blocks