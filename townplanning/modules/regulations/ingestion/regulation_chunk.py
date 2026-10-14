"""
A portion of a regulation extracted from a single PDF page.

One page may contain multiple RegulationChunks.

The RegulationAssembler merges chunks having the same
regulation number into a complete RegulationDocument.
"""

from dataclasses import dataclass, field

from townplanning.modules.regulations.ingestion.table import ExtractedTable


@dataclass(slots=True)
class RegulationChunk:
    number: str
    title: str

    chapter_number: str
    chapter_title: str

    page: int

    text: str

    tables: list[ExtractedTable] = field(default_factory=list)