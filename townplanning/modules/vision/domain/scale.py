from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Scale:
    """
    Represents drawing scale.

    Example:
        1:100
        1:200
        1:500
    """

    numerator: int = 1

    denominator: int = 100

    source_text: str | None = None

    @property
    def ratio(self) -> float:
        """
        Returns scale ratio.

        Example:
            1:100 -> 100
        """
        return float(self.denominator)

    def __str__(self) -> str:
        return f"{self.numerator}:{self.denominator}"