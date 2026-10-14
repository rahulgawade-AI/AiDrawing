from __future__ import annotations

from collections import defaultdict
from typing import Any

from townplanning.modules.vision.domain.vision_observation import (
    VisionEvidence,
    VisionObservation,
)


class EvidenceFusion:
    """
    Combines evidence from OCR, CV, AI and specialized detectors.

    Important:
        Fusion does NOT invent missing information.

    If two sources disagree, the disagreement is preserved.
    """

    def fuse(
        self,
        evidence_sets: list[VisionEvidence],
    ) -> VisionEvidence:

        result = VisionEvidence()

        all_observations: list[VisionObservation] = []

        for evidence in evidence_sets:

            if evidence.width is not None:
                result.width = evidence.width

            if evidence.height is not None:
                result.height = evidence.height

            all_observations.extend(
                evidence.observations
            )

        result.add_many(all_observations)

        self._fuse_classification(
            evidence_sets,
            result,
        )

        self._build_consensus(
            result,
        )

        return result

    def _fuse_classification(
        self,
        evidence_sets: list[VisionEvidence],
        result: VisionEvidence,
    ) -> None:

        scores: defaultdict[str, list[float]] = defaultdict(list)

        for evidence in evidence_sets:

            if evidence.image_type:
                scores[evidence.image_type].append(
                    evidence.image_type_confidence
                )

        if not scores:
            return

        weighted = {
            image_type: sum(values) / len(values)
            for image_type, values in scores.items()
        }

        image_type, confidence = max(
            weighted.items(),
            key=lambda item: item[1],
        )

        result.image_type = image_type
        result.image_type_confidence = min(
            1.0,
            confidence,
        )

    def _build_consensus(
        self,
        evidence: VisionEvidence,
    ) -> None:

        grouped: defaultdict[
            str,
            list[VisionObservation],
        ] = defaultdict(list)

        for observation in evidence.observations:
            grouped[
                observation.observation_type
            ].append(observation)

        for observation_type, observations in grouped.items():

            if len(observations) < 2:
                continue

            observations.sort(
                key=lambda x: x.confidence,
                reverse=True,
            )

            best = observations[0]

            # Check whether multiple sources agree.
            agreeing_sources = [
                x.source
                for x in observations
                if self._values_agree(
                    best.value,
                    x.value,
                )
            ]

            if len(agreeing_sources) >= 2:

                consensus_confidence = min(
                    0.99,
                    best.confidence + 0.10,
                )

                evidence.add(
                    VisionObservation(
                        observation_type=(
                            f"consensus:{observation_type}"
                        ),
                        value=best.value,
                        confidence=consensus_confidence,
                        source="evidence_fusion",
                        metadata={
                            "sources": agreeing_sources,
                            "source_count": len(
                                agreeing_sources
                            ),
                        },
                    )
                )

    @staticmethod
    def _values_agree(
        first: Any,
        second: Any,
    ) -> bool:

        if first is None or second is None:
            return False

        if isinstance(first, (int, float)) and isinstance(
            second,
            (int, float),
        ):
            if first == 0:
                return second == 0

            return (
                abs(float(first) - float(second))
                / abs(float(first))
                <= 0.05
            )

        return str(first).strip().lower() == str(
            second
        ).strip().lower()