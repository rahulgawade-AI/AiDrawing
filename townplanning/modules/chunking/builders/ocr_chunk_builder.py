from __future__ import annotations

from townplanning.modules.chunking.builders.base_chunk_builder import (
    BaseChunkBuilder,
)
from townplanning.modules.chunking.domain.chunk import Chunk
from townplanning.modules.retrieval.domain.source_document import SourceDocument


class OCRChunkBuilder(BaseChunkBuilder):
    """
    Builds semantic chunks from OCR documents.

    OCR text is split by paragraphs and grouped until the
    configured maximum size is reached.
    """

    MAX_CHARS = 1200

    def build(
        self,
        document: SourceDocument,
    ) -> list[Chunk]:

        text = self.normalize_text(document.text)

        if self.is_empty(text):
            return []

        paragraphs = self.split_paragraphs(text)

        chunks: list[Chunk] = []

        buffer = ""

        index = 1

        for paragraph in paragraphs:

            candidate = (
                paragraph
                if not buffer
                else f"{buffer}\n\n{paragraph}"
            )

            if len(candidate) <= self.MAX_CHARS:

                buffer = candidate

                continue

            chunks.append(
                self.create_chunk(
                    document=document,
                    chunk_index=index,
                    text=buffer,
                )
            )

            index += 1

            buffer = paragraph

        if buffer:

            chunks.append(
                self.create_chunk(
                    document=document,
                    chunk_index=index,
                    text=buffer,
                )
            )

        return chunks