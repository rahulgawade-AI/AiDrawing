from __future__ import annotations

from townplanning.modules.vision.domain.plot_boundary import (
    PlotBoundary,
)


class PlotMapper:

    def map(
        self,
        plot: PlotBoundary,
    ) -> PlotBoundary:

        return plot