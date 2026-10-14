"""
Structured regulatory table extracted from a PDF page.

This module contains source-preserving extraction models only.

IMPORTANT:
    This layer does NOT decide which regulatory value applies to a
    particular planning project.

It preserves:
    - raw headers
    - header rows
    - data rows
    - title
    - markdown
    - page/index
    - bounding box
    - extraction metadata
"""
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ExtractedTable:
    """
    Source-preserving representation of a PDF table.

    The object intentionally remains generic. It must be usable for
    FSI, height, floors, setbacks, parking, fire, open space, amenity,
    and any other UDCPR table.
    """

    id: str = field(
        default_factory=lambda: str(uuid4())
    )

    page: int = 0

    index: int = 0

    title: str = ""

    # First-row compatibility representation.
    headers: list[str] = field(
        default_factory=list
    )

    # All detected header rows.
    header_rows: list[list[str]] = field(
        default_factory=list
    )

    # Raw data rows.
    rows: list[list[str]] = field(
        default_factory=list
    )

    # Original extracted markdown.
    markdown: str = ""

    # Bounding box when available.
    bbox: tuple[float, float, float, float] | None = None

    # Generic source/extraction metadata.
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.page = int(self.page or 0)
        self.index = int(self.index or 0)

        if self.headers is None:
            self.headers = []

        if self.header_rows is None:
            self.header_rows = []

        if self.rows is None:
            self.rows = []

        if self.metadata is None:
            self.metadata = {}

        if self.bbox is not None:
            try:
                self.bbox = tuple(
                    float(value)
                    for value in self.bbox[:4]
                )
            except (TypeError, ValueError):
                self.bbox = None

    @property
    def source_page(self) -> int:
        return self.page

    @property
    def table_index(self) -> int:
        return self.index

    def all_header_rows(self) -> list[list[str]]:
        """
        Return all available header rows.

        Preserve the original `headers` field for backward compatibility.
        """
        if self.header_rows:
            return self.header_rows

        if self.headers:
            return [self.headers]

        return []

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "page": self.page,
            "index": self.index,
            "title": self.title,
            "headers": list(self.headers),
            "header_rows": [
                list(row)
                for row in self.header_rows
            ],
            "rows": [
                list(row)
                for row in self.rows
            ],
            "markdown": self.markdown,
            "bbox": list(self.bbox)
            if self.bbox is not None
            else None,
            "metadata": dict(self.metadata),
        }
