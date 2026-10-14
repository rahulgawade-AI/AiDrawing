from __future__ import annotations

import re
from abc import ABC
from abc import abstractmethod
from typing import Any
from uuid import uuid4

from townplanning.modules.chunking.domain.chunk import Chunk
from townplanning.modules.retrieval.domain.source_document import SourceDocument


class BaseChunkBuilder(ABC):
    """
    Base class for all chunk builders.

    Provides common functionality for creating semantic chunks
    from different document types (OCR, Regulations, Tables, etc.).
    """

    @abstractmethod
    def build(
        self,
        document: SourceDocument,
    ) -> list[Chunk]:
        """
        Convert a SourceDocument into semantic chunks.
        """
        raise NotImplementedError

    ####################################################################
    # Helper Methods
    ####################################################################

    def create_chunk(
        self,
        *,
        document: SourceDocument,
        chunk_index: int,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        """
        Create a Chunk object with common metadata.
        """

        chunk_metadata = document.metadata.copy()

        if metadata:
            chunk_metadata.update(metadata)

        return Chunk(
            id=str(uuid4()),
            source_type=document.source_type,
            source_id=document.source_id,
            chunk_index=chunk_index,
            title=document.title,
            text=text.strip(),
            page_number=document.page_number,
            metadata=chunk_metadata,
        )

    def normalize_text(
        self,
        text: str,
    ) -> str:
        """
        Normalize whitespace while preserving paragraph boundaries.
        """

        if not text:
            return ""

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Remove trailing spaces
        text = re.sub(r"[ \t]+", " ", text)

        # Keep only two consecutive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def split_paragraphs(
        self,
        text: str,
    ) -> list[str]:
        """
        Split text into paragraphs.
        """

        if not text:
            return []

        return [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ]

    def merge_metadata(
        self,
        document: SourceDocument,
        **extra: Any,
    ) -> dict[str, Any]:
        """
        Merge document metadata with additional metadata.
        """

        metadata = document.metadata.copy()
        metadata.update(extra)
        return metadata

    def is_empty(
        self,
        text: str,
    ) -> bool:
        """
        Check whether text contains useful content.
        """

        return not text or not text.strip()

    def exceeds_limit(
        self,
        text: str,
        limit: int,
    ) -> bool:
        """
        Check if text exceeds a configured character limit.
        """

        return len(text) > limit

    def combine_paragraphs(
        self,
        paragraphs: list[str],
    ) -> str:
        """
        Join paragraphs while preserving paragraph boundaries.
        """

        return "\n\n".join(paragraphs)