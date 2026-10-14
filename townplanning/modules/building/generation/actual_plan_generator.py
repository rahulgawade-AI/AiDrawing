from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ezdxf
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from shapely.geometry import Polygon, box


# ============================================================
# DATA MODELS
# ============================================================


@dataclass
class Room:
    name: str
    room_type: str
    x: float
    y: float
    width: float
    depth: float

    @property
    def area(self) -> float:
        return self.width * self.depth


@dataclass
class Door:
    x: float
    y: float
    width: float
    orientation: str = "horizontal"


@dataclass
class Window:
    x: float
    y: float
    width: float
    orientation: str = "horizontal"


@dataclass
class Unit:
    unit_id: str
    unit_type: str
    x: float
    y: float
    width: float
    depth: float
    rooms: list[Room] = field(default_factory=list)
    doors: list[Door] = field(default_factory=list)
    windows: list[Window] = field(default_factory=list)

    @property
    def area(self) -> float:
        return self.width * self.depth


@dataclass
class Building:
    building_id: str
    x: float
    y: float
    width: float
    depth: float
    floors: int
    units: list[Unit] = field(default_factory=list)
    common_spaces: list[Room] = field(default_factory=list)

    @property
    def footprint_area(self) -> float:
        return self.width * self.depth


@dataclass
class SitePlan:
    plot: Polygon
    buildable_area: Polygon
    buildings: list[Building]
    road_width: float
    setbacks: dict[str, float]
    total_fsi_area: float
    fsi: float

    @property
    def building_count(self) -> int:
        return len(self.buildings)

    @property
    def total_units(self) -> int:
        return sum(
            len(building.units) * building.floors
            for building in self.buildings
        )


# ============================================================
# GENERATOR
# ============================================================


class ActualBuildingPlanGenerator:
    """
    Deterministic architectural floor-plan generator.

    Ollama may decide upstream:
        - building count
        - floors
        - unit mix
        - preferred unit program

    This class owns actual geometry.

    It does NOT allow an LLM to invent arbitrary wall
    coordinates.
    """

    WALL = 0.20

    def __init__(
        self,
        output_dir: str | Path = "/tmp/building_plan",
    ) -> None:

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ========================================================
    # PUBLIC API
    # ========================================================

    def generate(
        self,
        *,
        plot_coordinates: list[tuple[float, float]],
        plot_area: float,
        road_width: float,
        fsi: float,
        floors: int = 5,
        units_per_floor: int = 3,
        front_setback: float = 3.0,
        rear_setback: float = 3.0,
        side_setback: float = 1.5,
        unit_mix: list[str] | None = None,
    ) -> SitePlan:

        if not plot_coordinates:
            raise ValueError(
                "plot_coordinates are required."
            )

        if floors <= 0:
            raise ValueError(
                "floors must be positive."
            )

        if units_per_floor <= 0:
            raise ValueError(
                "units_per_floor must be positive."
            )

        plot = Polygon(plot_coordinates)

        if not plot.is_valid:
            plot = plot.buffer(0)

        if plot.is_empty:
            raise ValueError(
                "Invalid plot polygon."
            )

        # ----------------------------------------------------
        # Check supplied area against geometry.
        # ----------------------------------------------------

        geometric_area = plot.area

        if geometric_area <= 0:
            raise ValueError(
                "Plot geometry has zero area."
            )

        # Do not silently rescale the plot.
        # A mismatch is reported but the geometry itself
        # remains authoritative.
        area_difference = abs(
            geometric_area - plot_area
        )

        area_difference_percent = (
            area_difference / plot_area * 100
            if plot_area
            else 0
        )

        # ----------------------------------------------------
        # Buildable envelope.
        # ----------------------------------------------------

        buildable = self._buildable_polygon(
            plot,
            front_setback,
            rear_setback,
            side_setback,
        )

        if buildable.is_empty:
            raise ValueError(
                "No buildable area remains after setbacks."
            )

        # ----------------------------------------------------
        # FSI.
        # ----------------------------------------------------

        target_fsi_area = (
            plot_area * fsi
        )

        # ----------------------------------------------------
        # Building footprint.
        # ----------------------------------------------------

        footprint = self._select_footprint(
            buildable,
            target_fsi_area,
            floors,
        )

        if footprint is None:
            raise ValueError(
                "Unable to generate building footprint."
            )

        minx, miny, maxx, maxy = (
            footprint.bounds
        )

        building = Building(
            building_id="B01",
            x=minx,
            y=miny,
            width=maxx - minx,
            depth=maxy - miny,
            floors=floors,
        )

        # ----------------------------------------------------
        # Unit mix.
        # ----------------------------------------------------

        if unit_mix is None:
            unit_mix = self._default_unit_mix(
                units_per_floor
            )

        if len(unit_mix) != units_per_floor:
            raise ValueError(
                "unit_mix length must equal "
                "units_per_floor."
            )

        # ----------------------------------------------------
        # Generate architectural floor layout.
        # ----------------------------------------------------

        building.units = self._generate_units(
            building,
            unit_mix,
        )

        building.common_spaces = (
            self._generate_common_spaces(
                building
            )
        )

        # ----------------------------------------------------
        # Site.
        # ----------------------------------------------------

        site = SitePlan(
            plot=plot,
            buildable_area=buildable,
            buildings=[building],
            road_width=road_width,
            setbacks={
                "front": front_setback,
                "rear": rear_setback,
                "side": side_setback,
            },
            total_fsi_area=target_fsi_area,
            fsi=fsi,
        )

        # ----------------------------------------------------
        # Validate.
        # ----------------------------------------------------

        self.validate(site)

        # ----------------------------------------------------
        # Export.
        # ----------------------------------------------------

        self.export_png(
            site,
            self.output_dir / "site_plan.png",
        )

        self.export_dxf(
            site,
            self.output_dir / "site_plan.dxf",
        )

        self.export_floor_plans(
            site
        )

        self.export_units(
            site
        )

        self._write_report(
            site,
            plot_area=plot_area,
            geometric_plot_area=geometric_area,
            area_difference_percent=area_difference_percent,
        )

        return site

    # ========================================================
    # BUILDABLE AREA
    # ========================================================

    def _buildable_polygon(
        self,
        plot: Polygon,
        front: float,
        rear: float,
        side: float,
    ) -> Polygon:

        """
        Conservative geometry.

        Until the road-facing plot edge is explicitly encoded,
        the maximum setback is applied around the full perimeter.

        This is intentionally conservative.
        """

        setback = max(
            float(front),
            float(rear),
            float(side),
        )

        if setback <= 0:
            return plot

        buildable = plot.buffer(
            -setback,
            join_style=2,
        )

        if buildable.is_empty:
            return Polygon()

        if buildable.geom_type == "MultiPolygon":
            buildable = max(
                buildable.geoms,
                key=lambda item: item.area,
            )

        return buildable

    # ========================================================
    # FOOTPRINT
    # ========================================================

    def _select_footprint(
        self,
        buildable: Polygon,
        target_fsi_area: float,
        floors: int,
    ) -> Polygon | None:

        """
        Select a practical rectangular building footprint.

        The FSI target is an upper limit.

        We search for a rectangle whose total floor area is
        as close as possible to the permitted FSI area while
        remaining completely inside the buildable polygon.
        """

        desired_floor_area = (
            target_fsi_area / floors
        )

        if desired_floor_area <= 0:
            return None

        minx, miny, maxx, maxy = (
            buildable.bounds
        )

        available_width = (
            maxx - minx
        )

        available_depth = (
            maxy - miny
        )

        if (
            available_width <= 0
            or available_depth <= 0
        ):
            return None

        # ----------------------------------------------------
        # Candidate floor areas.
        #
        # Prefer using the maximum FSI permitted.
        # ----------------------------------------------------

        area_factors = (
            1.00,
            0.98,
            0.96,
            0.94,
            0.92,
            0.90,
            0.88,
            0.85,
            0.80,
            0.75,
        )

        aspect_ratios = (
            0.70,
            0.75,
            0.80,
            0.85,
            0.90,
            0.95,
            1.00,
            1.05,
            1.10,
            1.15,
            1.20,
            1.25,
            1.30,
            1.35,
            1.40,
        )

        best: tuple[float, Polygon] | None = None

        for factor in area_factors:

            requested_area = (
                desired_floor_area
                * factor
            )

            for aspect in aspect_ratios:

                width = math.sqrt(
                    requested_area
                    * aspect
                )

                depth = (
                    requested_area
                    / width
                )

                if (
                    width > available_width
                    or depth > available_depth
                ):
                    continue

                # ------------------------------------------------
                # Grid search.
                # ------------------------------------------------

                for ix in range(31):

                    x = (
                        minx
                        + (
                            available_width
                            - width
                        )
                        * ix
                        / 30
                    )

                    for iy in range(31):

                        y = (
                            miny
                            + (
                                available_depth
                                - depth
                            )
                            * iy
                            / 30
                        )

                        candidate = box(
                            x,
                            y,
                            x + width,
                            y + depth,
                        )

                        if not buildable.covers(
                            candidate
                        ):
                            continue

                        # Prefer:
                        # 1. larger floor area
                        # 2. reasonable aspect ratio
                        score = (
                            abs(
                                desired_floor_area
                                - candidate.area
                            )
                            + abs(
                                math.log(
                                    aspect
                                )
                            )
                            * 5
                        )

                        if (
                            best is None
                            or score < best[0]
                        ):
                            best = (
                                score,
                                candidate,
                            )

            # Once a candidate exists at this factor,
            # don't unnecessarily shrink it further.
            if best is not None:
                return best[1]

        return None

    # ========================================================
    # UNIT MIX
    # ========================================================

    def _default_unit_mix(
        self,
        units_per_floor: int,
    ) -> list[str]:

        if units_per_floor == 1:
            return ["3BHK"]

        if units_per_floor == 2:
            return [
                "2BHK",
                "2BHK",
            ]

        if units_per_floor == 3:
            return [
                "2BHK",
                "2BHK",
                "1BHK",
            ]

        if units_per_floor == 4:
            return [
                "2BHK",
                "2BHK",
                "1BHK",
                "1BHK",
            ]

        return [
            "2BHK"
            for _ in range(
                units_per_floor
            )
        ]

    # ========================================================
    # UNIT GENERATION
    # ========================================================

    def _generate_units(
        self,
        building: Building,
        unit_mix: list[str],
    ) -> list[Unit]:

        """
        Architectural arrangement for three units:

                    NORTH
        ┌─────────┬──────┬─────────┐
        │         │      │         │
        │  2BHK   │CORR. │  2BHK   │
        │         │      │         │
        ├─────────┴──────┼─────────┤
        │       1BHK     │  CORE   │
        │                │ STAIR   │
        │                │ LIFT    │
        └────────────────┴─────────┘
                    SOUTH

        This avoids the old "three vertical strips" problem.
        """

        if len(unit_mix) != 3:
            return self._generate_generic_units(
                building,
                unit_mix,
            )

        w = building.width
        d = building.depth

        # ----------------------------------------------------
        # Horizontal split.
        # ----------------------------------------------------

        bottom_depth = max(
            7.5,
            min(
                9.0,
                d * 0.43,
            ),
        )

        top_depth = (
            d - bottom_depth
        )

        if top_depth < 9.0:
            bottom_depth = d * 0.40
            top_depth = (
                d - bottom_depth
            )

        # ----------------------------------------------------
        # Central circulation strip.
        # ----------------------------------------------------

        corridor_width = min(
            2.0,
            w * 0.12,
        )

        if corridor_width < 1.5:
            corridor_width = 1.5

        side_width = (
            w - corridor_width
        ) / 2

        # ----------------------------------------------------
        # U01 - top left.
        # ----------------------------------------------------

        u01 = Unit(
            unit_id="U01",
            unit_type=unit_mix[0],
            x=building.x,
            y=building.y + bottom_depth,
            width=side_width,
            depth=top_depth,
        )

        # ----------------------------------------------------
        # U02 - top right.
        # ----------------------------------------------------

        u02 = Unit(
            unit_id="U02",
            unit_type=unit_mix[1],
            x=(
                building.x
                + side_width
                + corridor_width
            ),
            y=building.y + bottom_depth,
            width=side_width,
            depth=top_depth,
        )

        # ----------------------------------------------------
        # U03 - bottom left.
        # ----------------------------------------------------

        bottom_unit_width = (
            w * 0.55
        )

        u03 = Unit(
            unit_id="U03",
            unit_type=unit_mix[2],
            x=building.x,
            y=building.y,
            width=bottom_unit_width,
            depth=bottom_depth,
        )

        units = [
            u01,
            u02,
            u03,
        ]

        # ----------------------------------------------------
        # Generate rooms.
        # ----------------------------------------------------

        for unit in units:

            unit.rooms = (
                self._generate_rooms(
                    unit
                )
            )

            unit.doors = (
                self._generate_doors(
                    unit
                )
            )

            unit.windows = (
                self._generate_windows(
                    unit
                )
            )

        return units

    # ========================================================
    # GENERIC UNIT FALLBACK
    # ========================================================

    def _generate_generic_units(
        self,
        building: Building,
        unit_mix: list[str],
    ) -> list[Unit]:

        count = len(unit_mix)

        if count <= 0:
            return []

        width = (
            building.width / count
        )

        units = []

        for index, unit_type in enumerate(
            unit_mix,
            start=1,
        ):

            unit = Unit(
                unit_id=f"U{index:02d}",
                unit_type=unit_type,
                x=(
                    building.x
                    + (index - 1)
                    * width
                ),
                y=building.y,
                width=width,
                depth=building.depth,
            )

            unit.rooms = (
                self._generate_rooms(
                    unit
                )
            )

            unit.doors = (
                self._generate_doors(
                    unit
                )
            )

            unit.windows = (
                self._generate_windows(
                    unit
                )
            )

            units.append(unit)

        return units

    # ========================================================
    # COMMON CORE
    # ========================================================

    def _generate_common_spaces(
        self,
        building: Building,
    ) -> list[Room]:

        """
        Common circulation/core occupies the area not assigned
        to the three apartments.
        """

        x = building.x
        y = building.y

        w = building.width
        d = building.depth

        spaces: list[Room] = []

        # Central vertical corridor.
        corridor_width = min(
            2.0,
            w * 0.12,
        )

        corridor_x = (
            x
            + (w - corridor_width)
            / 2
        )

        bottom_depth = max(
            7.5,
            min(
                9.0,
                d * 0.43,
            ),
        )

        top_depth = (
            d - bottom_depth
        )

        if len(building.units) == 3:

            # ------------------------------------------------
            # Corridor.
            # ------------------------------------------------

            spaces.append(
                Room(
                    name="Common Corridor",
                    room_type="corridor",
                    x=corridor_x,
                    y=y + bottom_depth,
                    width=corridor_width,
                    depth=top_depth,
                )
            )

            # ------------------------------------------------
            # Bottom-right core.
            # ------------------------------------------------

            u03 = building.units[2]

            core_x = (
                u03.x
                + u03.width
            )

            core_width = (
                building.x
                + w
                - core_x
            )

            if core_width > 2.0:

                # Lift.
                lift_width = min(
                    2.2,
                    core_width * 0.40,
                )

                lift_depth = 2.2

                spaces.append(
                    Room(
                        name="Lift",
                        room_type="lift",
                        x=core_x + 0.5,
                        y=y + bottom_depth * 0.35,
                        width=lift_width,
                        depth=lift_depth,
                    )
                )

                # Staircase.
                stair_x = (
                    core_x
                    + core_width * 0.50
                )

                stair_width = (
                    core_width * 0.42
                )

                stair_depth = min(
                    5.0,
                    bottom_depth * 0.70,
                )

                spaces.append(
                    Room(
                        name="Staircase",
                        room_type="staircase",
                        x=stair_x,
                        y=y + 1.0,
                        width=stair_width,
                        depth=stair_depth,
                    )
                )

                # Lift lobby.
                spaces.append(
                    Room(
                        name="Lift Lobby",
                        room_type="lobby",
                        x=core_x + 0.3,
                        y=y + bottom_depth * 0.72,
                        width=max(
                            core_width - 0.6,
                            1.5,
                        ),
                        depth=max(
                            bottom_depth * 0.20,
                            1.5,
                        ),
                    )
                )

        return spaces

    # ========================================================
    # ROOM GENERATION
    # ========================================================

    def _generate_rooms(
        self,
        unit: Unit,
    ) -> list[Room]:

        if unit.unit_type.upper() == "1BHK":
            return self._rooms_1bhk(unit)

        if unit.unit_type.upper() == "3BHK":
            return self._rooms_3bhk(unit)

        return self._rooms_2bhk(unit)

    # ========================================================
    # 2BHK
    # ========================================================

    def _rooms_2bhk(
        self,
        unit: Unit,
    ) -> list[Room]:

        x = unit.x
        y = unit.y
        w = unit.width
        d = unit.depth

        rooms: list[Room] = []

        # ----------------------------------------------------
        # Keep sensible minimum proportions.
        # ----------------------------------------------------

        living_w = max(
            4.0,
            w * 0.58,
        )

        living_d = min(
            4.0,
            d * 0.32,
        )

        kitchen_w = w - living_w

        kitchen_d = min(
            3.0,
            d * 0.25,
        )

        bedroom_band_y = (
            y
            + living_d
        )

        bedroom_band_d = (
            d
            - living_d
        )

        if bedroom_band_d < 5.5:
            bedroom_band_d = 5.5

        # ----------------------------------------------------
        # Living / dining.
        # ----------------------------------------------------

        rooms.append(
            Room(
                name="Living / Dining",
                room_type="living",
                x=x,
                y=y + d - living_d,
                width=living_w,
                depth=living_d,
            )
        )

        # ----------------------------------------------------
        # Kitchen.
        # ----------------------------------------------------

        rooms.append(
            Room(
                name="Kitchen",
                room_type="kitchen",
                x=x + living_w,
                y=y + d - kitchen_d,
                width=kitchen_w,
                depth=kitchen_d,
            )
        )

        # ----------------------------------------------------
        # Bedroom zone.
        # ----------------------------------------------------

        bed_gap = 0.20

        master_w = (
            w * 0.52
        )

        second_w = (
            w
            - master_w
            - bed_gap
        )

        master_d = min(
            3.8,
            bedroom_band_d * 0.55,
        )

        second_d = min(
            3.6,
            bedroom_band_d * 0.52,
        )

        # Master bedroom.
        rooms.append(
            Room(
                name="Master Bedroom",
                room_type="bedroom",
                x=x,
                y=y + 0.20,
                width=master_w,
                depth=master_d,
            )
        )

        # Attached toilet.
        toilet_w = min(
            1.70,
            master_w * 0.40,
        )

        toilet_d = 2.10

        rooms.append(
            Room(
                name="Attached Toilet",
                room_type="toilet",
                x=(
                    x
                    + master_w
                    - toilet_w
                ),
                y=(
                    y
                    + master_d
                    - toilet_d
                ),
                width=toilet_w,
                depth=toilet_d,
            )
        )

        # Bedroom 2.
        rooms.append(
            Room(
                name="Bedroom 2",
                room_type="bedroom",
                x=x + master_w + bed_gap,
                y=y + 0.20,
                width=second_w,
                depth=second_d,
            )
        )

        # Common toilet.
        common_w = min(
            1.70,
            second_w * 0.48,
        )

        rooms.append(
            Room(
                name="Common Toilet",
                room_type="toilet",
                x=(
                    x
                    + w
                    - common_w
                ),
                y=(
                    y
                    + second_d
                    - 2.10
                ),
                width=common_w,
                depth=2.10,
            )
        )

        # Utility.
        utility_w = min(
            2.0,
            kitchen_w,
        )

        utility_d = min(
            1.50,
            d * 0.12,
        )

        rooms.append(
            Room(
                name="Utility",
                room_type="utility",
                x=(
                    x
                    + w
                    - utility_w
                ),
                y=y + d - kitchen_d - utility_d,
                width=utility_w,
                depth=utility_d,
            )
        )

        return rooms

    # ========================================================
    # 1BHK
    # ========================================================

    def _rooms_1bhk(
        self,
        unit: Unit,
    ) -> list[Room]:

        x = unit.x
        y = unit.y
        w = unit.width
        d = unit.depth

        rooms: list[Room] = []

        living_d = min(
            3.8,
            d * 0.40,
        )

        kitchen_w = min(
            3.0,
            w * 0.38,
        )

        bedroom_d = min(
            3.8,
            d * 0.50,
        )

        toilet_w = min(
            1.80,
            w * 0.28,
        )

        toilet_d = 2.10

        # Living.
        rooms.append(
            Room(
                name="Living / Dining",
                room_type="living",
                x=x,
                y=y + d - living_d,
                width=w,
                depth=living_d,
            )
        )

        # Kitchen.
        rooms.append(
            Room(
                name="Kitchen",
                room_type="kitchen",
                x=x + w - kitchen_w,
                y=y + d - living_d - 3.0,
                width=kitchen_w,
                depth=3.0,
            )
        )

        # Bedroom.
        rooms.append(
            Room(
                name="Bedroom",
                room_type="bedroom",
                x=x,
                y=y + 0.20,
                width=w - toilet_w - 0.20,
                depth=bedroom_d,
            )
        )

        # Toilet.
        rooms.append(
            Room(
                name="Toilet",
                room_type="toilet",
                x=x + w - toilet_w,
                y=y + 0.20,
                width=toilet_w,
                depth=toilet_d,
            )
        )

        # Utility.
        rooms.append(
            Room(
                name="Utility",
                room_type="utility",
                x=x + w - kitchen_w,
                y=y + d - living_d - 1.5,
                width=kitchen_w,
                depth=1.5,
            )
        )

        return rooms

    # ========================================================
    # 3BHK
    # ========================================================

    def _rooms_3bhk(
        self,
        unit: Unit,
    ) -> list[Room]:

        x = unit.x
        y = unit.y
        w = unit.width
        d = unit.depth

        rooms: list[Room] = []

        living_d = min(
            4.0,
            d * 0.28,
        )

        rooms.append(
            Room(
                name="Living / Dining",
                room_type="living",
                x=x,
                y=y + d - living_d,
                width=w,
                depth=living_d,
            )
        )

        lower_d = d - living_d

        col_w = (
            w / 2
        )

        bed_d = min(
            3.8,
            lower_d * 0.52,
        )

        rooms.append(
            Room(
                name="Master Bedroom",
                room_type="bedroom",
                x=x,
                y=y + lower_d - bed_d,
                width=col_w,
                depth=bed_d,
            )
        )

        rooms.append(
            Room(
                name="Bedroom 2",
                room_type="bedroom",
                x=x + col_w,
                y=y + lower_d - bed_d,
                width=col_w,
                depth=bed_d,
            )
        )

        rooms.append(
            Room(
                name="Bedroom 3",
                room_type="bedroom",
                x=x,
                y=y + 0.20,
                width=col_w,
                depth=max(
                    lower_d - bed_d - 0.4,
                    2.5,
                ),
            )
        )

        rooms.append(
            Room(
                name="Kitchen",
                room_type="kitchen",
                x=x + col_w,
                y=y + 0.20,
                width=col_w * 0.65,
                depth=3.0,
            )
        )

        rooms.append(
            Room(
                name="Common Toilet",
                room_type="toilet",
                x=x + w - 1.70,
                y=y + 0.20,
                width=1.70,
                depth=2.10,
            )
        )

        rooms.append(
            Room(
                name="Attached Toilet",
                room_type="toilet",
                x=x + col_w - 1.70,
                y=y + lower_d - bed_d + 0.20,
                width=1.70,
                depth=2.10,
            )
        )

        return rooms

    # ========================================================
    # DOORS
    # ========================================================

    def _generate_doors(
        self,
        unit: Unit,
    ) -> list[Door]:

        doors: list[Door] = []

        # Main entrance.
        doors.append(
            Door(
                x=unit.x + unit.width / 2,
                y=unit.y,
                width=1.0,
                orientation="horizontal",
            )
        )

        # Bedroom doors.
        for room in unit.rooms:

            if room.room_type in {
                "bedroom",
                "kitchen",
                "toilet",
            }:

                doors.append(
                    Door(
                        x=room.x + room.width / 2,
                        y=room.y,
                        width=0.8,
                        orientation="horizontal",
                    )
                )

        return doors

    # ========================================================
    # WINDOWS
    # ========================================================

    def _generate_windows(
        self,
        unit: Unit,
    ) -> list[Window]:

        windows: list[Window] = []

        for room in unit.rooms:

            if room.room_type in {
                "living",
                "bedroom",
                "kitchen",
            }:

                windows.append(
                    Window(
                        x=room.x + room.width / 2,
                        y=room.y + room.depth,
                        width=min(
                            1.8,
                            room.width * 0.55,
                        ),
                        orientation="horizontal",
                    )
                )

        return windows

    # ========================================================
    # VALIDATION
    # ========================================================

    def validate(
        self,
        site: SitePlan,
    ) -> None:

        if not site.buildings:
            raise ValueError(
                "No building generated."
            )

        if site.plot.area <= 0:
            raise ValueError(
                "Invalid plot area."
            )

        maximum_fsi_area = (
            site.total_fsi_area
        )

        total_floor_area = 0.0

        for building in site.buildings:

            footprint = box(
                building.x,
                building.y,
                building.x + building.width,
                building.y + building.depth,
            )

            # ------------------------------------------------
            # Building must fit completely.
            # ------------------------------------------------

            if not site.buildable_area.covers(
                footprint
            ):
                raise ValueError(
                    f"{building.building_id} "
                    "extends outside buildable area."
                )

            if building.footprint_area <= 0:
                raise ValueError(
                    f"{building.building_id} "
                    "has invalid footprint."
                )

            total_floor_area += (
                building.footprint_area
                * building.floors
            )

            if (
                total_floor_area
                > maximum_fsi_area
                + 0.01
            ):
                raise ValueError(
                    "Generated floor area exceeds "
                    "permitted FSI area."
                )

            if not building.units:
                raise ValueError(
                    f"{building.building_id} "
                    "contains no units."
                )

            # ------------------------------------------------
            # Unit validation.
            # ------------------------------------------------

            unit_polygons = []

            for unit in building.units:

                unit_polygon = box(
                    unit.x,
                    unit.y,
                    unit.x + unit.width,
                    unit.y + unit.depth,
                )

                unit_polygons.append(
                    unit_polygon
                )

                if not footprint.covers(
                    unit_polygon
                ):
                    raise ValueError(
                        f"{unit.unit_id} "
                        "extends outside building."
                    )

                if unit.area <= 0:
                    raise ValueError(
                        f"{unit.unit_id} "
                        "has invalid area."
                    )

                for room in unit.rooms:

                    room_polygon = box(
                        room.x,
                        room.y,
                        room.x + room.width,
                        room.y + room.depth,
                    )

                    if not unit_polygon.covers(
                        room_polygon
                    ):
                        raise ValueError(
                            f"{room.name} in "
                            f"{unit.unit_id} "
                            "extends outside unit."
                        )

                    if room.area <= 0:
                        raise ValueError(
                            f"{room.name} "
                            "has invalid area."
                        )

                    # Prevent absurd room proportions.
                    longest = max(
                        room.width,
                        room.depth,
                    )

                    shortest = min(
                        room.width,
                        room.depth,
                    )

                    if (
                        shortest > 0
                        and longest / shortest > 5.5
                    ):
                        raise ValueError(
                            f"{room.name} in "
                            f"{unit.unit_id} "
                            "has unreasonable "
                            "room proportions."
                        )

            # ------------------------------------------------
            # Units may touch but cannot overlap.
            # ------------------------------------------------

            for i in range(
                len(unit_polygons)
            ):

                for j in range(
                    i + 1,
                    len(unit_polygons),
                ):

                    intersection = (
                        unit_polygons[i]
                        .intersection(
                            unit_polygons[j]
                        )
                    )

                    if intersection.area > 0.01:
                        raise ValueError(
                            "Units overlap."
                        )

            # ------------------------------------------------
            # Common spaces.
            # ------------------------------------------------

            for room in (
                building.common_spaces
            ):

                common_polygon = box(
                    room.x,
                    room.y,
                    room.x + room.width,
                    room.y + room.depth,
                )

                if not footprint.covers(
                    common_polygon
                ):
                    raise ValueError(
                        f"Common space "
                        f"{room.name} extends "
                        "outside building."
                    )

    # ========================================================
    # SITE PNG
    # ========================================================

    def export_png(
        self,
        site: SitePlan,
        path: Path,
    ) -> None:

        fig, ax = plt.subplots(
            figsize=(12, 10)
        )

        # Plot.
        x, y = site.plot.exterior.xy

        ax.plot(
            x,
            y,
            linewidth=2.5,
            label="Plot Boundary",
        )

        # Buildable.
        bx, by = (
            site.buildable_area.exterior.xy
        )

        ax.plot(
            bx,
            by,
            linestyle="--",
            linewidth=1.5,
            label="Buildable Area",
        )

        for building in site.buildings:

            ax.add_patch(
                Rectangle(
                    (
                        building.x,
                        building.y,
                    ),
                    building.width,
                    building.depth,
                    fill=False,
                    linewidth=3,
                )
            )

            ax.text(
                building.x
                + building.width / 2,
                building.y
                + building.depth / 2,
                (
                    f"{building.building_id}\n"
                    f"{building.floors} Floors"
                ),
                ha="center",
                va="center",
                fontsize=12,
            )

        # North arrow.
        minx, miny, maxx, maxy = (
            site.plot.bounds
        )

        arrow_x = (
            minx
            + (maxx - minx) * 0.90
        )

        arrow_y = (
            miny
            + (maxy - miny) * 0.82
        )

        ax.annotate(
            "N",
            xy=(
                arrow_x,
                arrow_y + 4,
            ),
            xytext=(
                arrow_x,
                arrow_y,
            ),
            arrowprops={
                "arrowstyle": "->",
                "linewidth": 2,
            },
            fontsize=18,
            ha="center",
        )

        ax.set_title(
            "Residential Building Site Plan"
        )

        ax.set_xlabel(
            "Meters"
        )

        ax.set_ylabel(
            "Meters"
        )

        ax.set_aspect(
            "equal",
            adjustable="box",
        )

        ax.grid(
            True,
            alpha=0.20,
        )

        ax.legend()

        fig.tight_layout()

        fig.savefig(
            path,
            dpi=180,
            bbox_inches="tight",
        )

        plt.close(fig)

    # ========================================================
    # FLOOR PNG
    # ========================================================

    def export_floor_plans(
        self,
        site: SitePlan,
    ) -> None:

        for building in site.buildings:

            for floor in range(
                1,
                building.floors + 1,
            ):

                path = (
                    self.output_dir
                    / (
                        f"{building.building_id}"
                        f"_floor_{floor:02d}.png"
                    )
                )

                self._export_floor_png(
                    building,
                    path,
                    floor,
                )

                dxf_path = (
                    self.output_dir
                    / (
                        f"{building.building_id}"
                        f"_floor_{floor:02d}.dxf"
                    )
                )

                self._export_floor_dxf(
                    building,
                    dxf_path,
                    floor,
                )

    def _export_floor_png(
        self,
        building: Building,
        path: Path,
        floor: int,
    ) -> None:

        fig, ax = plt.subplots(
            figsize=(15, 12)
        )

        # Building boundary.
        ax.add_patch(
            Rectangle(
                (
                    building.x,
                    building.y,
                ),
                building.width,
                building.depth,
                fill=False,
                linewidth=3,
            )
        )

        # Common spaces.
        for room in (
            building.common_spaces
        ):

            self._draw_room(
                ax,
                room,
            )

        # Units and rooms.
        for unit in building.units:

            ax.add_patch(
                Rectangle(
                    (
                        unit.x,
                        unit.y,
                    ),
                    unit.width,
                    unit.depth,
                    fill=False,
                    linewidth=2,
                )
            )

            for room in unit.rooms:

                self._draw_room(
                    ax,
                    room,
                )

            # Unit label.
            ax.text(
                unit.x
                + unit.width / 2,
                unit.y
                + unit.depth
                - 0.45,
                (
                    f"{unit.unit_id} "
                    f"{unit.unit_type}"
                ),
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
            )

            # Windows.
            for window in (
                unit.windows
            ):

                ax.plot(
                    [
                        window.x
                        - window.width / 2,
                        window.x
                        + window.width / 2,
                    ],
                    [
                        window.y,
                        window.y,
                    ],
                    linewidth=4,
                )

            # Doors.
            for door in (
                unit.doors
            ):

                ax.plot(
                    [
                        door.x
                        - door.width / 2,
                        door.x
                        + door.width / 2,
                    ],
                    [
                        door.y,
                        door.y,
                    ],
                    linewidth=5,
                )

        ax.set_title(
            f"B01 - Floor {floor} "
            "Residential Floor Plan"
        )

        ax.set_xlabel(
            "Meters"
        )

        ax.set_ylabel(
            "Meters"
        )

        ax.set_aspect(
            "equal",
            adjustable="box",
        )

        ax.grid(
            True,
            alpha=0.15,
        )

        fig.tight_layout()

        fig.savefig(
            path,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close(fig)

    def _draw_room(
        self,
        ax: Any,
        room: Room,
    ) -> None:

        ax.add_patch(
            Rectangle(
                (
                    room.x,
                    room.y,
                ),
                room.width,
                room.depth,
                fill=False,
                linewidth=1.2,
            )
        )

        ax.text(
            room.x
            + room.width / 2,
            room.y
            + room.depth / 2,
            (
                f"{room.name}\n"
                f"{room.width:.2f} × "
                f"{room.depth:.2f} m\n"
                f"{room.area:.1f} m²"
            ),
            ha="center",
            va="center",
            fontsize=7,
        )

    # ========================================================
    # UNIT PNG/DXF
    # ========================================================

    def export_units(
        self,
        site: SitePlan,
    ) -> None:

        for building in site.buildings:

            for unit in building.units:

                png_path = (
                    self.output_dir
                    / (
                        f"{unit.unit_id}_"
                        f"{unit.unit_type}.png"
                    )
                )

                dxf_path = (
                    self.output_dir
                    / (
                        f"{unit.unit_id}_"
                        f"{unit.unit_type}.dxf"
                    )
                )

                self._export_unit_png(
                    unit,
                    png_path,
                )

                self._export_unit_dxf(
                    unit,
                    dxf_path,
                )

    def _export_unit_png(
        self,
        unit: Unit,
        path: Path,
    ) -> None:

        fig, ax = plt.subplots(
            figsize=(12, 9)
        )

        ax.add_patch(
            Rectangle(
                (
                    unit.x,
                    unit.y,
                ),
                unit.width,
                unit.depth,
                fill=False,
                linewidth=3,
            )
        )

        for room in unit.rooms:

            self._draw_room(
                ax,
                room,
            )

        for window in unit.windows:

            ax.plot(
                [
                    window.x
                    - window.width / 2,
                    window.x
                    + window.width / 2,
                ],
                [
                    window.y,
                    window.y,
                ],
                linewidth=4,
            )

        for door in unit.doors:

            ax.plot(
                [
                    door.x
                    - door.width / 2,
                    door.x
                    + door.width / 2,
                ],
                [
                    door.y,
                    door.y,
                ],
                linewidth=5,
            )

        ax.set_title(
            f"{unit.unit_id} "
            f"{unit.unit_type} "
            f"Apartment"
        )

        ax.set_xlabel(
            "Meters"
        )

        ax.set_ylabel(
            "Meters"
        )

        ax.set_aspect(
            "equal",
            adjustable="box",
        )

        ax.grid(
            True,
            alpha=0.15,
        )

        fig.tight_layout()

        fig.savefig(
            path,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close(fig)

    # ========================================================
    # DXF HELPERS
    # ========================================================

    def _new_dxf(self):
        doc = ezdxf.new(
            "R2013"
        )

        msp = doc.modelspace()

        for layer_name in (
            "WALLS",
            "ROOMS",
            "TEXT",
            "WINDOWS",
            "DOORS",
            "CORE",
            "SITE",
        ):

            if layer_name not in doc.layers:
                doc.layers.new(
                    layer_name
                )

        return doc, msp

    def _rect_dxf(
        self,
        msp,
        x: float,
        y: float,
        width: float,
        depth: float,
        layer: str,
    ):

        points = [
            (x, y),
            (x + width, y),
            (
                x + width,
                y + depth,
            ),
            (x, y + depth),
            (x, y),
        ]

        msp.add_lwpolyline(
            points,
            dxfattribs={
                "layer": layer,
            },
        )

    def _text_dxf(
        self,
        msp,
        text: str,
        x: float,
        y: float,
        height: float = 0.25,
        layer: str = "TEXT",
    ):

        msp.add_text(
            text,
            dxfattribs={
                "height": height,
                "layer": layer,
            },
        ).set_placement(
            (
                x,
                y,
            )
        )

    # ========================================================
    # SITE DXF
    # ========================================================

    def export_dxf(
        self,
        site: SitePlan,
        path: Path,
    ) -> None:

        doc, msp = self._new_dxf()

        # Plot.
        coords = list(
            site.plot.exterior.coords
        )

        msp.add_lwpolyline(
            coords,
            dxfattribs={
                "layer": "SITE",
            },
        )

        # Buildable.
        coords = list(
            site.buildable_area.exterior.coords
        )

        msp.add_lwpolyline(
            coords,
            dxfattribs={
                "layer": "SITE",
            },
        )

        for building in site.buildings:

            self._rect_dxf(
                msp,
                building.x,
                building.y,
                building.width,
                building.depth,
                "WALLS",
            )

            self._text_dxf(
                msp,
                (
                    f"{building.building_id} "
                    f"{building.floors} FLOORS"
                ),
                building.x
                + building.width / 2,
                building.y
                + building.depth / 2,
            )

        doc.saveas(
            path
        )

    # ========================================================
    # FLOOR DXF
    # ========================================================

    def _export_floor_dxf(
        self,
        building: Building,
        path: Path,
        floor: int,
    ) -> None:

        doc, msp = self._new_dxf()

        self._rect_dxf(
            msp,
            building.x,
            building.y,
            building.width,
            building.depth,
            "WALLS",
        )

        for room in (
            building.common_spaces
        ):

            layer = (
                "CORE"
                if room.room_type
                in {
                    "lift",
                    "staircase",
                    "lobby",
                }
                else "ROOMS"
            )

            self._rect_dxf(
                msp,
                room.x,
                room.y,
                room.width,
                room.depth,
                layer,
            )

            self._text_dxf(
                msp,
                room.name,
                room.x + room.width / 2,
                room.y + room.depth / 2,
                0.20,
                "TEXT",
            )

        for unit in building.units:

            self._rect_dxf(
                msp,
                unit.x,
                unit.y,
                unit.width,
                unit.depth,
                "WALLS",
            )

            self._text_dxf(
                msp,
                (
                    f"{unit.unit_id} "
                    f"{unit.unit_type}"
                ),
                unit.x + unit.width / 2,
                unit.y + unit.depth - 0.4,
                0.25,
                "TEXT",
            )

            for room in unit.rooms:

                self._rect_dxf(
                    msp,
                    room.x,
                    room.y,
                    room.width,
                    room.depth,
                    "ROOMS",
                )

                self._text_dxf(
                    msp,
                    room.name,
                    room.x + room.width / 2,
                    room.y + room.depth / 2,
                    0.18,
                    "TEXT",
                )

            for window in unit.windows:

                msp.add_line(
                    (
                        window.x
                        - window.width / 2,
                        window.y,
                    ),
                    (
                        window.x
                        + window.width / 2,
                        window.y,
                    ),
                    dxfattribs={
                        "layer": "WINDOWS",
                    },
                )

            for door in unit.doors:

                msp.add_line(
                    (
                        door.x
                        - door.width / 2,
                        door.y,
                    ),
                    (
                        door.x
                        + door.width / 2,
                        door.y,
                    ),
                    dxfattribs={
                        "layer": "DOORS",
                    },
                )

        self._text_dxf(
            msp,
            f"FLOOR {floor}",
            building.x,
            building.y
            + building.depth
            + 1.0,
            0.30,
        )

        doc.saveas(
            path
        )

    # ========================================================
    # UNIT DXF
    # ========================================================

    def _export_unit_dxf(
        self,
        unit: Unit,
        path: Path,
    ) -> None:

        doc, msp = self._new_dxf()

        self._rect_dxf(
            msp,
            unit.x,
            unit.y,
            unit.width,
            unit.depth,
            "WALLS",
        )

        self._text_dxf(
            msp,
            (
                f"{unit.unit_id} "
                f"{unit.unit_type}"
            ),
            unit.x + unit.width / 2,
            unit.y + unit.depth + 0.5,
            0.30,
        )

        for room in unit.rooms:

            self._rect_dxf(
                msp,
                room.x,
                room.y,
                room.width,
                room.depth,
                "ROOMS",
            )

            self._text_dxf(
                msp,
                room.name,
                room.x + room.width / 2,
                room.y + room.depth / 2,
                0.18,
                "TEXT",
            )

        for window in unit.windows:

            msp.add_line(
                (
                    window.x
                    - window.width / 2,
                    window.y,
                ),
                (
                    window.x
                    + window.width / 2,
                    window.y,
                ),
                dxfattribs={
                    "layer": "WINDOWS",
                },
            )

        for door in unit.doors:

            msp.add_line(
                (
                    door.x
                    - door.width / 2,
                    door.y,
                ),
                (
                    door.x
                    + door.width / 2,
                    door.y,
                ),
                dxfattribs={
                    "layer": "DOORS",
                },
            )

        doc.saveas(
            path
        )

    # ========================================================
    # REPORT
    # ========================================================

    def _write_report(
        self,
        site: SitePlan,
        *,
        plot_area: float,
        geometric_plot_area: float,
        area_difference_percent: float,
    ) -> None:

        buildings = []

        for building in site.buildings:

            units = []

            for unit in building.units:

                units.append(
                    {
                        "unit_id": unit.unit_id,
                        "unit_type": unit.unit_type,
                        "area_m2": round(
                            unit.area,
                            2,
                        ),
                        "rooms": [
                            {
                                "name": room.name,
                                "type": room.room_type,
                                "x": round(
                                    room.x,
                                    3,
                                ),
                                "y": round(
                                    room.y,
                                    3,
                                ),
                                "width_m": round(
                                    room.width,
                                    3,
                                ),
                                "depth_m": round(
                                    room.depth,
                                    3,
                                ),
                                "area_m2": round(
                                    room.area,
                                    2,
                                ),
                            }
                            for room
                            in unit.rooms
                        ],
                    }
                )

            buildings.append(
                {
                    "building_id":
                        building.building_id,
                    "x": building.x,
                    "y": building.y,
                    "width_m":
                        round(
                            building.width,
                            3,
                        ),
                    "depth_m":
                        round(
                            building.depth,
                            3,
                        ),
                    "footprint_area_m2":
                        round(
                            building.footprint_area,
                            2,
                        ),
                    "floors":
                        building.floors,
                    "units_per_floor":
                        len(
                            building.units
                        ),
                    "floor_area_m2":
                        round(
                            building.footprint_area,
                            2,
                        ),
                    "total_floor_area_m2":
                        round(
                            building.footprint_area
                            * building.floors,
                            2,
                        ),
                    "common_spaces": [
                        {
                            "name": room.name,
                            "type": room.room_type,
                            "width_m": round(
                                room.width,
                                3,
                            ),
                            "depth_m": round(
                                room.depth,
                                3,
                            ),
                            "area_m2": round(
                                room.area,
                                2,
                            ),
                        }
                        for room
                        in building.common_spaces
                    ],
                    "units": units,
                }
            )

        report = {
            "plot_area_input_m2":
                plot_area,

            "plot_area_geometry_m2":
                round(
                    geometric_plot_area,
                    2,
                ),

            "plot_area_difference_percent":
                round(
                    area_difference_percent,
                    3,
                ),

            "road_width_m":
                site.road_width,

            "fsi":
                site.fsi,

            "maximum_fsi_area_m2":
                round(
                    site.total_fsi_area,
                    2,
                ),

            "setbacks_m":
                site.setbacks,

            "building_count":
                site.building_count,

            "total_units":
                site.total_units,

            "buildings":
                buildings,
        }

        path = (
            self.output_dir
            / "design_report.json"
        )

        path.write_text(
            json.dumps(
                report,
                indent=2,
            )
        )


# ============================================================
# END
# ============================================================
