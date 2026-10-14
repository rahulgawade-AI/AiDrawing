"""
Structured models produced by the Document Analyzer.

These models represent the semantic understanding
of a single PDF page.
"""

from pydantic import BaseModel
from pydantic import Field


class RegulationHeading(BaseModel):
    """
    One regulation heading detected on the page.
    """

    number: str = Field(
        description="Regulation number, e.g. 5.1.1"
    )

    title: str = Field(
        description="Regulation title"
    )


class PageAnalysis(BaseModel):
    """
    Structured analysis of a PDF page.
    """

    page_type: str = Field(
        description=(
            "chapter | regulation | table | "
            "appendix | schedule | index | form | other"
        )
    )

    chapter_number: str | None = None

    chapter_title: str | None = None

    regulations: list[RegulationHeading] = Field(
        default_factory=list
    )

    contains_table: bool = False

    contains_figure: bool = False

    contains_appendix: bool = False

    contains_schedule: bool = False

    contains_forms: bool = False

    contains_index: bool = False

    summary: str = ""

    keywords: list[str] = Field(
        default_factory=list
    )