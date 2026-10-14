from __future__ import annotations

from townplanning.modules.vision.domain.text_block import TextBlock


class ConfidenceScorer:

    def filter(
        self,
        blocks: list[TextBlock],
        minimum: float = 0.60,
    ) -> list[TextBlock]:

        return [

            block

            for block in blocks

            if block.confidence >= minimum

        ]

    def sort(
        self,
        blocks: list[TextBlock],
    ) -> list[TextBlock]:

        return sorted(

            blocks,

            key=lambda b: b.confidence,

            reverse=True,

        )