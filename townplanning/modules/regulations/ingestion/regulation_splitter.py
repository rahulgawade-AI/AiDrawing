"""
Split a page into one or more RegulationChunks.

DocumentAnalyzer already identifies all regulation headings
on the page.

This class simply slices the page text between those headings.

No AI is used here.
"""

from __future__ import annotations

import logging
import re

from townplanning.modules.regulations.ingestion.regulation_chunk import (
    RegulationChunk,
)

logger = logging.getLogger(__name__)


class RegulationSplitter:
    """
    Split page text into regulation chunks.

    Example:

        8.1 Height

        text....

        text....

        8.2 FSI

        text....

    becomes

        Chunk(8.1)

        Chunk(8.2)
    """

    def split(
        self,
        analysis,
        window,
    ) -> list[RegulationChunk]:

        text = window.current_text or ""

        if not text.strip():
            return []

        if not analysis.regulations:
            return []

        #
        # Find heading positions
        #
        positions = []

        for heading in analysis.regulations:

            idx = self._find_heading_position(
                text,
                heading.number,
                heading.title,
            )

            if idx >= 0:

                positions.append(
                    (
                        idx,
                        heading,
                    )
                )

            else:

                logger.warning(
                    "Could not locate heading %s on page %s",
                    heading.number,
                    window.current_page,
                )

        if not positions:
            return []

        #
        # Sort by text position
        #
        positions.sort(key=lambda x: x[0])

        chunks = []

        #
        # Slice text
        #
        for i, (start, heading) in enumerate(positions):

            if i == len(positions) - 1:

                end = len(text)

            else:

                end = positions[i + 1][0]

            chunk_text = text[start:end].strip()

            if not chunk_text:
                continue

            chunks.append(
                RegulationChunk(
                    number=heading.number,
                    title=heading.title,
                    chapter_number=analysis.chapter_number or "",
                    chapter_title=analysis.chapter_title or "",
                    page=window.current_page,
                    text=chunk_text,
                    tables=[],
                )
            )

        logger.info(
            "Split page %s into %s regulation chunks",
            window.current_page,
            len(chunks),
        )

        return chunks

    # --------------------------------------------------------

    def _find_heading_position(
        self,
        text: str,
        number: str,
        title: str,
    ) -> int:
        """
        Locate the regulation heading.

        Tries several increasingly relaxed strategies.
        """

        #
        # Strategy 1
        #
        if title:

            pattern = (
                rf"{re.escape(number)}\s*[-.:)]?\s*"
                rf"{re.escape(title)}"
            )

            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
            )

            if match:
                return match.start()

        #
        # Strategy 2
        #
        match = re.search(
            rf"\b{re.escape(number)}\b",
            text,
        )

        if match:
            return match.start()

        #
        # Strategy 3
        #
        idx = text.find(number)

        if idx >= 0:
            return idx

        return -1