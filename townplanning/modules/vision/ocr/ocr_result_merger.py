from __future__ import annotations

from townplanning.modules.vision.domain.text_block import TextBlock


class OCRResultMerger:

    """
    Simple confidence-based merger.

    IoU and duplicate suppression
    will be added later.
    """

    def merge(
        self,
        *passes: list[TextBlock],
    ) -> list[TextBlock]:

        merged = {}

        for result in passes:

            for block in result:

                key = block.text.strip()

                if key not in merged:

                    merged[key] = block

                elif block.confidence > merged[key].confidence:

                    merged[key] = block

        return list(
            merged.values()
        )