"""
Assembled regulation spanning one or more PDF pages.

Produced by RegulationAssembler.

This is the input to the KnowledgeExtractor.
"""

from dataclasses import dataclass, field

from townplanning.modules.regulations.ingestion.table import ExtractedTable


@dataclass(slots=True)
class RegulationDocument:

    id: str

    number: str

    title: str

    chapter_number: str

    chapter_title: str

    language: str

    start_page: int

    end_page: int

    text: str

    tables: list[ExtractedTable] = field(default_factory=list)