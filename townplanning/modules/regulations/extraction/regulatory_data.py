"""
Generic structured regulatory data.

This module represents extracted regulatory information without
performing project-specific regulatory calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RegulatoryValue:
    """
    A value extracted from UDCPR source material.

    Examples:
        2.25
        12.0 m
        1:100
        "< 9.0 m"
        "Residential"
        "Municipal Corporation"
    """

    field: str

    value: Any

    unit: str | None = None

    condition: dict[str, Any] = field(
        default_factory=dict
    )

    source_page: int | None = None

    source_table_id: str | None = None

    source_regulation: str | None = None

    source_text: str | None = None

    confidence: float = 1.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "unit": self.unit,
            "condition": dict(
                self.condition
            ),
            "source_page": self.source_page,
            "source_table_id": (
                self.source_table_id
            ),
            "source_regulation": (
                self.source_regulation
            ),
            "source_text": self.source_text,
            "confidence": self.confidence,
            "metadata": dict(
                self.metadata
            ),
        }


@dataclass(slots=True)
class RegulatoryTableData:
    """
    Generic semantic representation of an extracted table.

    No project-specific selection happens here.
    """

    table_id: str

    title: str

    page: int

    headers: list[str] = field(
        default_factory=list
    )

    header_rows: list[list[str]] = field(
        default_factory=list
    )

    rows: list[list[str]] = field(
        default_factory=list
    )

    identified_fields: list[str] = field(
        default_factory=list
    )

    identified_conditions: list[str] = field(
        default_factory=list
    )

    values: list[RegulatoryValue] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_id": self.table_id,
            "title": self.title,
            "page": self.page,
            "headers": list(self.headers),
            "header_rows": [
                list(row)
                for row in self.header_rows
            ],
            "rows": [
                list(row)
                for row in self.rows
            ],
            "identified_fields": list(
                self.identified_fields
            ),
            "identified_conditions": list(
                self.identified_conditions
            ),
            "values": [
                value.to_dict()
                for value in self.values
            ],
            "metadata": dict(
                self.metadata
            ),
        }
