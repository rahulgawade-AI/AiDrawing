from __future__ import annotations

from townplanning.modules.vision.domain.road import Road


class RoadMapper:

    def map(
        self,
        roads: list[Road],
    ) -> list[Road]:

        return roads