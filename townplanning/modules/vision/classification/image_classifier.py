from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from townplanning.modules.vision.domain.image_type import ImageType
from townplanning.modules.vision.domain.vision_observation import (
    VisionEvidence,
    VisionObservation,
)


class ImageClassifier:
    """
    General-purpose image classifier.

    IMPORTANT:
    This classifier must NOT assume that every image is
    a site plan, CAD drawing, or photograph.

    It produces weak local evidence.

    A multimodal AI model can provide additional evidence.
    """

    SITE_TERMS = (
        "plot",
        "layout",
        "site",
        "survey",
        "road",
        "road width",
        "plot area",
        "sq.m",
        "sqm",
        "boundary",
        "property",
        "north",
        "scale",
        "survey no",
        "survey number",
        "cts",
    )

    FLOOR_TERMS = (
        "bedroom",
        "bed room",
        "kitchen",
        "toilet",
        "bath",
        "living",
        "dining",
        "stair",
        "stairs",
        "lift",
        "door",
        "window",
        "room",
        "wc",
    )

    CAD_TERMS = (
        "cad",
        "dimension",
        "dimensions",
        "section",
        "elevation",
        "all dimensions",
    )

    SATELLITE_TERMS = (
        "google earth",
        "satellite",
        "imagery",
        "aerial",
    )

    MAP_TERMS = (
        "map",
        "street",
        "highway",
        "road",
        "north",
        "scale",
    )

    def classify(
        self,
        image: Any,
        ocr_text: str | None = None,
        image_path: str | Path | None = None,
    ) -> VisionEvidence:

        array = self._to_array(image)

        height, width = array.shape[:2]

        evidence = VisionEvidence(
            width=width,
            height=height,
        )

        scores: dict[ImageType, float] = {
            image_type: 0.0
            for image_type in ImageType
        }

        text = self._normalise_text(
            ocr_text
        )

        # --------------------------------------------------
        # OCR/text evidence
        # --------------------------------------------------

        self._score_text(
            text,
            scores,
        )

        # --------------------------------------------------
        # Visual evidence
        # --------------------------------------------------

        self._score_visual_structure(
            array,
            scores,
        )

        # --------------------------------------------------
        # Document/photo evidence
        # --------------------------------------------------

        photo_score = self._photo_score(
            array
        )

        document_score = self._document_score(
            array
        )

        scores[ImageType.PHOTOGRAPH] += photo_score
        scores[ImageType.DOCUMENT_SCAN] += document_score

        # --------------------------------------------------
        # IMPORTANT:
        #
        # Never allow photograph to win merely because
        # edge variance is high.
        # --------------------------------------------------

        # Technical evidence suppresses photograph classification.
        technical_score = max(
            scores[ImageType.SITE_PLAN],
            scores[ImageType.SURVEY_PLAN],
            scores[ImageType.FLOOR_PLAN],
            scores[ImageType.CAD_DRAWING],
            scores[ImageType.MAP],
        )

        if technical_score > 0.25:
            scores[ImageType.PHOTOGRAPH] *= 0.25

        # --------------------------------------------------
        # Select candidate.
        # --------------------------------------------------

        image_type, score = max(
            scores.items(),
            key=lambda item: item[1],
        )

        # Do not classify an image from weak evidence.
        if score < 0.30:
            image_type = ImageType.UNKNOWN
            score = 0.0

        score = min(
            1.0,
            float(score),
        )

        evidence.image_type = image_type.value
        evidence.image_type_confidence = score

        evidence.add(
            VisionObservation(
                observation_type="image_classification",
                value=image_type.value,
                confidence=score,
                source="classifier",
                metadata={
                    "scores": {
                        key.value: round(
                            value,
                            4,
                        )
                        for key, value in scores.items()
                    },
                    "ocr_used": bool(text),
                    "image_path": (
                        str(image_path)
                        if image_path
                        else None
                    ),
                },
            )
        )

        return evidence

    # ======================================================
    # IMAGE CONVERSION
    # ======================================================

    @staticmethod
    def _to_array(
        image: Any,
    ) -> np.ndarray:

        if isinstance(
            image,
            np.ndarray,
        ):
            return image

        if isinstance(
            image,
            (str, Path),
        ):

            array = cv2.imread(
                str(image)
            )

            if array is None:
                raise ValueError(
                    f"Unable to read image: {image}"
                )

            return array

        if hasattr(
            image,
            "shape",
        ):
            return np.asarray(
                image
            )

        raise TypeError(
            f"Unsupported image type: {type(image)!r}"
        )

    # ======================================================
    # TEXT
    # ======================================================

    @staticmethod
    def _normalise_text(
        text: str | None,
    ) -> str:

        if not text:
            return ""

        return re.sub(
            r"\s+",
            " ",
            text.lower(),
        ).strip()

    def _score_text(
        self,
        text: str,
        scores: dict[ImageType, float],
    ) -> None:

        if not text:
            return

        site_hits = sum(
            term in text
            for term in self.SITE_TERMS
        )

        floor_hits = sum(
            term in text
            for term in self.FLOOR_TERMS
        )

        cad_hits = sum(
            term in text
            for term in self.CAD_TERMS
        )

        satellite_hits = sum(
            term in text
            for term in self.SATELLITE_TERMS
        )

        map_hits = sum(
            term in text
            for term in self.MAP_TERMS
        )

        # ----------------------------------------------
        # Site / survey
        # ----------------------------------------------

        scores[
            ImageType.SITE_PLAN
        ] += min(
            0.75,
            site_hits * 0.10,
        )

        scores[
            ImageType.SURVEY_PLAN
        ] += min(
            0.65,
            site_hits * 0.08,
        )

        # ----------------------------------------------
        # Floor plan
        # ----------------------------------------------

        scores[
            ImageType.FLOOR_PLAN
        ] += min(
            0.75,
            floor_hits * 0.10,
        )

        # ----------------------------------------------
        # CAD
        # ----------------------------------------------

        scores[
            ImageType.CAD_DRAWING
        ] += min(
            0.50,
            cad_hits * 0.08,
        )

        # ----------------------------------------------
        # Satellite / aerial
        # ----------------------------------------------

        scores[
            ImageType.SATELLITE_IMAGE
        ] += min(
            0.70,
            satellite_hits * 0.15,
        )

        # ----------------------------------------------
        # Map
        # ----------------------------------------------

        scores[
            ImageType.MAP
        ] += min(
            0.60,
            map_hits * 0.10,
        )

        # Strong phrases.
        if re.search(
            r"\bplot\s+area\b",
            text,
        ):
            scores[
                ImageType.SITE_PLAN
            ] += 0.25

        if re.search(
            r"\bsurvey\s+(no|number)\b",
            text,
        ):
            scores[
                ImageType.SURVEY_PLAN
            ] += 0.25

        if re.search(
            r"\b(all\s+)?dimensions?\b",
            text,
        ):
            scores[
                ImageType.CAD_DRAWING
            ] += 0.15

        if re.search(
            r"\b(scale|north)\b",
            text,
        ):
            scores[
                ImageType.SITE_PLAN
            ] += 0.10

    # ======================================================
    # VISUAL STRUCTURE
    # ======================================================

    def _score_visual_structure(
        self,
        image: np.ndarray,
        scores: dict[ImageType, float],
    ) -> None:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        edges = cv2.Canny(
            gray,
            50,
            150,
        )

        edge_ratio = (
            float(
                np.count_nonzero(edges)
            )
            / float(edges.size)
        )

        # Thin-line technical drawing evidence.
        if 0.01 <= edge_ratio <= 0.12:

            scores[
                ImageType.CAD_DRAWING
            ] += 0.10

        # Strong line structure.
        if edge_ratio >= 0.025:

            scores[
                ImageType.SITE_PLAN
            ] += 0.08

            scores[
                ImageType.FLOOR_PLAN
            ] += 0.08

        # --------------------------------------------------
        # Large white background.
        # --------------------------------------------------

        white_ratio = float(
            np.count_nonzero(
                gray > 240
            )
        ) / float(gray.size)

        if white_ratio > 0.55:

            scores[
                ImageType.DOCUMENT_SCAN
            ] += 0.10

            scores[
                ImageType.CAD_DRAWING
            ] += 0.08

        # --------------------------------------------------
        # Colour evidence.
        # --------------------------------------------------

        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV,
        )

        saturation = hsv[:, :, 1]

        saturated_ratio = float(
            np.count_nonzero(
                saturation > 80
            )
        ) / float(
            saturation.size
        )

        # Highly saturated images are more likely to be
        # aerial/satellite/photo material.
        if saturated_ratio > 0.25:

            scores[
                ImageType.SATELLITE_IMAGE
            ] += 0.20

            scores[
                ImageType.AERIAL_IMAGE
            ] += 0.10

        # Very low saturation is common in technical drawings.
        if saturated_ratio < 0.08:

            scores[
                ImageType.CAD_DRAWING
            ] += 0.08

    # ======================================================
    # PHOTO SCORE
    # ======================================================

    @staticmethod
    def _photo_score(
        image: np.ndarray,
    ) -> float:

        """
        Conservative photograph detector.

        IMPORTANT:
        Edge sharpness alone is NOT sufficient.

        A technical drawing can have very high edge
        variance.
        """

        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV,
        )

        saturation = hsv[:, :, 1]

        value = hsv[:, :, 2]

        saturation_std = float(
            np.std(
                saturation
            )
        )

        value_std = float(
            np.std(
                value
            )
        )

        # Photos generally have richer tonal variation.
        tonal_score = min(
            0.20,
            value_std / 255.0 * 0.25,
        )

        colour_score = min(
            0.20,
            saturation_std / 128.0 * 0.20,
        )

        # Keep this intentionally weak.
        return tonal_score + colour_score

    # ======================================================
    # DOCUMENT SCORE
    # ======================================================

    @staticmethod
    def _document_score(
        image: np.ndarray,
    ) -> float:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        white_ratio = float(
            np.count_nonzero(
                gray > 240
            )
        ) / float(
            gray.size
        )

        if white_ratio > 0.75:
            return 0.20

        if white_ratio > 0.55:
            return 0.10

        return 0.0