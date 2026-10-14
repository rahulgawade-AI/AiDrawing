from __future__ import annotations

from typing import Dict

from townplanning.modules.chunking.builders.base_chunk_builder import (
    BaseChunkBuilder,
)
from townplanning.modules.chunking.builders.ocr_chunk_builder import (
    OCRChunkBuilder,
)
from townplanning.modules.chunking.builders.regulation_chunk_builder import (
    RegulationChunkBuilder,
)
from townplanning.modules.chunking.builders.table_chunk_builder import (
    TableChunkBuilder,
)
from townplanning.modules.chunking.domain.chunk import Chunk
from townplanning.modules.retrieval.domain.source_document import (
    SourceDocument,
)
from townplanning.modules.retrieval.domain.source_type import (
    SourceType,
)


class ChunkingService:
    """
    Service responsible for converting SourceDocument objects into
    semantic chunks.

    A specific ChunkBuilder is selected based on the document's
    SourceType.
    """

    def __init__(self) -> None:
        self._builders: Dict[
            SourceType,
            BaseChunkBuilder,
        ] = {
            SourceType.OCR: OCRChunkBuilder(),
            SourceType.REGULATION: RegulationChunkBuilder(),
            SourceType.TABLE: TableChunkBuilder(),
        }

    def chunk_document(
        self,
        document: SourceDocument,
    ) -> list[Chunk]:
        """
        Create semantic chunks from a SourceDocument.

        Args:
            document:
                Source document to be chunked.

        Returns:
            List of generated Chunk objects.

        Raises:
            ValueError:
                If no builder is registered for the document source type.
        """

        builder = self._builders.get(document.source_type)

        if builder is None:
            raise ValueError(
                f"No chunk builder registered for source type "
                f"'{document.source_type.name}'."
            )

        return builder.build(document)

    def register_builder(
        self,
        source_type: SourceType,
        builder: BaseChunkBuilder,
        overwrite: bool = False,
    ) -> None:
        """
        Register a custom chunk builder.

        Args:
            source_type:
                Source type handled by the builder.

            builder:
                Chunk builder instance.

            overwrite:
                Replace an existing builder if True.

        Raises:
            ValueError:
                If a builder already exists and overwrite=False.
        """

        if (
            source_type in self._builders
            and not overwrite
        ):
            raise ValueError(
                f"Chunk builder already registered for "
                f"{source_type.name}."
            )

        self._builders[source_type] = builder

    def unregister_builder(
        self,
        source_type: SourceType,
    ) -> None:
        """
        Remove a registered builder.
        """

        self._builders.pop(source_type, None)

    def has_builder(
        self,
        source_type: SourceType,
    ) -> bool:
        """
        Check whether a builder exists.
        """

        return source_type in self._builders

    def get_builder(
        self,
        source_type: SourceType,
    ) -> BaseChunkBuilder | None:
        """
        Return the registered builder for a source type.
        """

        return self._builders.get(source_type)

    @property
    def supported_source_types(
        self,
    ) -> list[SourceType]:
        """
        Return all supported source types.
        """

        return list(self._builders.keys())