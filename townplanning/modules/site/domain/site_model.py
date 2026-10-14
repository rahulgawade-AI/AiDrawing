from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from townplanning.modules.vision.domain.dimension import Dimension
from townplanning.modules.vision.domain.polygon import Polygon
from townplanning.modules.vision.domain.road import Road
from townplanning.modules.vision.domain.text_block import TextBlock


@dataclass(slots=True)
class SiteModel:
    """
    Canonical representation of a development site.

    Every module in the planning system consumes this object.

    Sources:
        - Plot drawing
        - OCR
        - Vision
        - Planning maps
        - User inputs
        - GIS data
    """

    #
    # Identity
    #
    id: UUID = field(default_factory=uuid4)

    created_at: datetime = field(default_factory=datetime.utcnow)

    #
    # Uploaded drawing information
    #
    drawing_name: str | None = None

    page_number: int = 1

    #
    # Plot Geometry
    #
    plot_boundary: Polygon | None = None

    buildable_polygon: Polygon | None = None

    #
    # Roads
    #
    roads: list[Road] = field(default_factory=list)

    #
    # OCR
    #
    text_blocks: list[TextBlock] = field(default_factory=list)

    dimensions: list[Dimension] = field(default_factory=list)

    #
    # Planning Metadata
    #
    planning_authority: str | None = None

    village: str | None = None

    survey_number: str | None = None

    city_survey_number: str | None = None

    zone: str | None = None

    reservation: str | None = None

    road_width: float | None = None

    plot_area: float | None = None

    north_angle: float | None = None

    #
    # Engineering (Sprint 4)
    #
    permissible_fsi: float | None = None

    premium_fsi: float | None = None

    max_height: float | None = None

    front_setback: float | None = None

    rear_setback: float | None = None

    side_setback_left: float | None = None

    side_setback_right: float | None = None

    parking_required: int | None = None

    #
    # User Requirements
    #
    requested_floors: int | None = None

    requested_bhk: int | None = None

    requested_parking: int | None = None

    requested_builtup_area: float | None = None

    #
    # Additional Metadata
    #
    metadata: dict[str, str] = field(default_factory=dict)

    #
    # Utility Methods
    #
    @property
    def has_plot(self) -> bool:
        return self.plot_boundary is not None

    @property
    def has_dimensions(self) -> bool:
        return len(self.dimensions) > 0

    @property
    def has_ocr(self) -> bool:
        return len(self.text_blocks) > 0

    @property
    def has_roads(self) -> bool:
        return len(self.roads) > 0

    @property
    def is_engineered(self) -> bool:
        """
        True once Engineering Engine
        has calculated planning constraints.
        """
        return self.permissible_fsi is not None

    def add_text(self, text: TextBlock) -> None:
        self.text_blocks.append(text)

    def add_dimension(self, dimension: Dimension) -> None:
        self.dimensions.append(dimension)

    def add_road(self, road: Road) -> None:
        self.roads.append(road)

    def set_plot(self, polygon: Polygon) -> None:
        self.plot_boundary = polygon

    def set_buildable_polygon(
        self,
        polygon: Polygon,
    ) -> None:
        self.buildable_polygon = polygon