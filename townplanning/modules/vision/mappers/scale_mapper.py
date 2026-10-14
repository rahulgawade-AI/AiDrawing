from __future__ import annotations

from townplanning.modules.vision.domain.scale import Scale


class ScaleMapper:

    def map(
        self,
        scale: Scale | None,
    ) -> Scale | None:

        return scale