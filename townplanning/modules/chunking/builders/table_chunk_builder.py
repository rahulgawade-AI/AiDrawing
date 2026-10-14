from __future__ import annotations

from townplanning.modules.chunking.builders.base_chunk_builder import (
    BaseChunkBuilder,
)
from townplanning.modules.chunking.domain.chunk import Chunk
from townplanning.modules.retrieval.domain.source_document import SourceDocument


class TableChunkBuilder(BaseChunkBuilder):
    """
    Builds chunks from extracted tables.

    Each table is currently stored as a single semantic chunk.
    Large-table splitting can be introduced later if required.
    """

    def build(
        self,
        document: SourceDocument,
    ) -> list[Chunk]:

        text = self.normalize_text(document.text)

        if self.is_empty(text):
            return []

        return [
            self.create_chunk(
                document=document,
                chunk_index=1,
                text=text,
            )
        ]