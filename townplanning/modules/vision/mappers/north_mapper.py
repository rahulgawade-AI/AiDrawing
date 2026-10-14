from __future__ import annotations

from townplanning.modules.vision.domain.north_arrow import (
    NorthArrow,
)


class NorthMapper:

    def map(
        self,
        north: NorthArrow | None,
    ) -> NorthArrow | None:

        return north