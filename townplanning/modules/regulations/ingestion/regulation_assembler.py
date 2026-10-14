"""
Assemble RegulationChunks into complete RegulationDocuments.

Responsibilities
----------------
- Merge chunks belonging to the same regulation.
- Detect when a new regulation starts.
- Emit completed RegulationDocument objects.
- Flush the final regulation at end of PDF.

This class contains NO AI.
"""

from __future__ import annotations

from uuid import uuid4

from townplanning.modules.regulations.ingestion.regulation_chunk import (
    RegulationChunk,
)

from townplanning.modules.regulations.ingestion.regulation_document import (
    RegulationDocument,
)


class RegulationAssembler:

    def __init__(self):

        self.current: RegulationDocument | None = None

    # ---------------------------------------------------------

    def add_chunk(
        self,
        chunk: RegulationChunk,
    ) -> RegulationDocument | None:

        #
        # First regulation
        #
        if self.current is None:

            self.current = self._create_document(chunk)

            return None

        #
        # Same regulation continues
        #
        if chunk.number == self.current.number:

            self.current.text += "\n\n"
            self.current.text += chunk.text

            self.current.end_page = chunk.page

            self.current.tables.extend(chunk.tables)

            return None

        #
        # New regulation encountered
        #
        completed = self.current

        self.current = self._create_document(chunk)

        return completed

    # ---------------------------------------------------------

    def flush(
        self,
    ) -> RegulationDocument | None:

        completed = self.current

        self.current = None

        return completed

    # ---------------------------------------------------------

    def reset(self):

        self.current = None

    # ---------------------------------------------------------

    def has_pending(self) -> bool:

        return self.current is not None

    # ---------------------------------------------------------

    def _create_document(
        self,
        chunk: RegulationChunk,
    ) -> RegulationDocument:

        return RegulationDocument(

            id=str(uuid4()),

            number=chunk.number,

            title=chunk.title,

            chapter_number=chunk.chapter_number,

            chapter_title=chunk.chapter_title,

            language="en",

            start_page=chunk.page,

            end_page=chunk.page,

            text=chunk.text,

            tables=list(chunk.tables),
        )