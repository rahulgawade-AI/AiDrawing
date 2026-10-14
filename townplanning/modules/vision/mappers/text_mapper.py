from __future__ import annotations

from townplanning.modules.vision.domain.text_block import TextBlock


class TextMapper:
    """
    Keeps only useful engineering text.
    """

    IGNORE = {
        "",
        ".",
        ",",
    }

    def map(
        self,
        blocks: list[TextBlock],
    ) -> list[TextBlock]:

        results = []

        for block in blocks:

            text = block.text.strip()

            if text in self.IGNORE:
                continue

            results.append(block)

        return results