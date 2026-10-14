from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2

from townplanning.modules.vision.classification.image_classifier import (
    ImageClassifier,
)
from townplanning.modules.vision.domain.vision_observation import (
    VisionEvidence,
)
from townplanning.modules.vision.ai.vision_analyzer import (
    VisionAnalyzer,
)
from townplanning.modules.vision.fusion.evidence_fusion import (
    EvidenceFusion,
)


class GeneralVisionService:
    """
    General-purpose perception layer.

    It accepts arbitrary images.

    It does NOT produce PlanningFacts.

    It produces evidence that the existing VisionService
    can consume.
    """

    def __init__(
        self,
        classifier: ImageClassifier | None = None,
        analyzer: VisionAnalyzer | None = None,
        fusion: EvidenceFusion | None = None,
        enable_ai: bool = True,
    ) -> None:

        self.classifier = (
            classifier
            or ImageClassifier()
        )

        self.analyzer = analyzer

        self.fusion = (
            fusion
            or EvidenceFusion()
        )

        self.enable_ai = enable_ai

    def analyze(
        self,
        image_path: str | Path,
        ocr_text: str | None = None,
    ) -> VisionEvidence:

        image_path = Path(image_path)

        image = cv2.imread(
            str(image_path)
        )

        if image is None:
            raise ValueError(
                f"Unable to load image: {image_path}"
            )

        evidence_sets: list[
            VisionEvidence
        ] = []

        # --------------------------------------------------
        # 1. Lightweight local classification
        # --------------------------------------------------

        classifier_evidence = (
            self.classifier.classify(
                image=image,
                ocr_text=ocr_text,
                image_path=image_path,
            )
        )

        evidence_sets.append(
            classifier_evidence
        )

        # --------------------------------------------------
        # 2. Optional multimodal AI
        # --------------------------------------------------

        if self.enable_ai:

            try:

                if self.analyzer is None:
                    self.analyzer = VisionAnalyzer()

                ai_evidence = (
                    self.analyzer.analyze(
                        image_path
                    )
                )

                evidence_sets.append(
                    ai_evidence
                )

            except Exception as exc:

                # AI is optional.
                # Local CV/OCR must continue to work.
                classifier_evidence.metadata[
                    "ai_error"
                ] = str(exc)

        # --------------------------------------------------
        # 3. Evidence fusion
        # --------------------------------------------------

        return self.fusion.fuse(
            evidence_sets
        )