from __future__ import annotations

from dataclasses import dataclass, field

from .page import Page


@dataclass(slots=True)
class Drawing:

    filename: str

    pages: list[Page] = field(default_factory=list)

    metadata: dict = field(default_factory=dict)