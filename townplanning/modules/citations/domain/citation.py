from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Citation:
    """
    Represents a citation used by an answer.
    """

    number: int

    source: str

    title: str | None = None

    page: int | None = None

    metadata: dict | None = None