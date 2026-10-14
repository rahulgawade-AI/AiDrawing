from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Room:
    name: str
    x: float
    y: float
    width: float
    depth: float
    room_type: str = "room"

    @property
    def area(self) -> float:
        return self.width * self.depth


@dataclass
class Door:
    x: float
    y: float
    width: float
    orientation: str


@dataclass
class Window:
    x: float
    y: float
    width: float
    orientation: str


@dataclass
class UnitPlan:
    unit_id: str
    unit_type: str
    carpet_area_m2: float
    width: float
    depth: float
    rooms: List[Room] = field(default_factory=list)
    doors: List[Door] = field(default_factory=list)
    windows: List[Window] = field(default_factory=list)


class ArchitecturalFloorPlanGenerator:
    """
    Generates enclosed residential unit layouts.

    Coordinate system:

        y = depth
        ^
        |
        |
        +------------> x

    Every room is represented by a rectangle.

    Design requirements:

    - rooms remain inside apartment boundary
    - rooms do not overlap
    - kitchen and bedrooms have separating walls
    - toilets are enclosed
    - utility is enclosed
    - rooms share boundaries
    - external rooms can receive windows
    """

    # ==========================================================
    # PUBLIC API
    # ==========================================================

    def generate_unit(
        self,
        unit_id: str,
        unit_type: str,
        carpet_area_m2: float,
    ) -> UnitPlan:

        if carpet_area_m2 <= 0:
            raise ValueError(
                "carpet_area_m2 must be greater than zero"
            )

        if unit_type == "1BHK":
            return self._generate_1bhk(
                unit_id,
                carpet_area_m2,
            )

        if unit_type == "2BHK":
            return self._generate_2bhk(
                unit_id,
                carpet_area_m2,
            )

        raise ValueError(
            f"Unsupported unit type: {unit_type}"
        )

    # ==========================================================
    # 1BHK
    # ==========================================================

    def _generate_1bhk(
        self,
        unit_id: str,
        target_area: float,
    ) -> UnitPlan:

        #
        # We don't blindly force:
        #
        # width * depth == carpet area
        #
        # because the architectural layout needs sensible
        # room proportions.
        #

        width = 8.40

        depth = max(
            8.40,
            target_area / width,
        )

        # ------------------------------------------------------
        # Horizontal bands
        #
        # +-----------------------+
        # | Living       |Kitchen |
        # |              |        |
        # +--------------+--------+
        # | Bedroom      | Toilet |
        # |              |        |
        # +--------------+--------+
        # | Bedroom      |Utility |
        # |              |        |
        # +--------------+--------+
        #
        # Every rectangle ends exactly at the unit boundary.
        # ------------------------------------------------------

        left_width = 5.10
        right_width = (
            width - left_width
        )

        living_height = max(
            2.80,
            depth * 0.32,
        )

        bedroom_height = max(
            3.20,
            depth * 0.43,
        )

        service_height = (
            depth
            - living_height
            - bedroom_height
        )

        # Prevent invalid geometry.
        if service_height < 1.50:

            service_height = 1.50

            bedroom_height = (
                depth
                - living_height
                - service_height
            )

        # ------------------------------------------------------
        # Y positions
        # ------------------------------------------------------

        y_service = 0.0

        y_bedroom = (
            service_height
        )

        y_living = (
            service_height
            + bedroom_height
        )

        # ------------------------------------------------------
        # Rooms
        # ------------------------------------------------------

        rooms = [

            # Living
            Room(
                name="Living / Dining",
                x=0.0,
                y=y_living,
                width=left_width,
                depth=living_height,
                room_type="living",
            ),

            # Kitchen
            Room(
                name="Kitchen",
                x=left_width,
                y=y_living,
                width=right_width,
                depth=living_height,
                room_type="kitchen",
            ),

            # Bedroom
            Room(
                name="Bedroom",
                x=0.0,
                y=y_bedroom,
                width=left_width,
                depth=bedroom_height,
                room_type="bedroom",
            ),

            # Toilet
            Room(
                name="Toilet",
                x=left_width,
                y=y_bedroom,
                width=right_width,
                depth=bedroom_height * 0.55,
                room_type="toilet",
            ),

            # Utility
            Room(
                name="Utility",
                x=left_width,
                y=y_service,
                width=right_width,
                depth=service_height,
                room_type="utility",
            ),

            # Remaining lower-left space becomes dining/
            # foyer rather than an artificial floating room.
            Room(
                name="Foyer",
                x=0.0,
                y=y_service,
                width=left_width,
                depth=service_height,
                room_type="foyer",
            ),
        ]

        # ------------------------------------------------------
        # Doors
        #
        # Doors are placed on shared walls.
        # ------------------------------------------------------

        doors = [

            # Living -> Bedroom
            Door(
                x=left_width,
                y=y_bedroom + bedroom_height * 0.72,
                width=0.90,
                orientation="vertical",
            ),

            # Living -> Kitchen
            Door(
                x=left_width,
                y=y_living + living_height * 0.45,
                width=0.90,
                orientation="vertical",
            ),

            # Bedroom -> Toilet
            Door(
                x=left_width,
                y=y_bedroom + bedroom_height * 0.30,
                width=0.75,
                orientation="vertical",
            ),

            # Foyer -> Living
            Door(
                x=left_width * 0.50,
                y=y_living,
                width=0.90,
                orientation="horizontal",
            ),
        ]

        # ------------------------------------------------------
        # Windows
        # ------------------------------------------------------

        windows = [

            # Living - north
            Window(
                x=1.20,
                y=depth,
                width=1.80,
                orientation="north",
            ),

            # Bedroom - west
            Window(
                x=0.0,
                y=y_bedroom + 1.00,
                width=1.60,
                orientation="west",
            ),

            # Kitchen - east
            Window(
                x=width,
                y=y_living + 0.80,
                width=1.40,
                orientation="east",
            ),

            # Utility - east
            Window(
                x=width,
                y=service_height * 0.35,
                width=1.20,
                orientation="east",
            ),
        ]

        return UnitPlan(
            unit_id=unit_id,
            unit_type="1BHK",
            carpet_area_m2=target_area,
            width=width,
            depth=depth,
            rooms=rooms,
            doors=doors,
            windows=windows,
        )

    # ==========================================================
    # 2BHK
    # ==========================================================

    def _generate_2bhk(
        self,
        unit_id: str,
        target_area: float,
    ) -> UnitPlan:

        #
        # Approximate architectural envelope.
        #

        width = 10.80

        depth = max(
            8.80,
            target_area / width,
        )

        # ------------------------------------------------------
        # Main vertical division
        # ------------------------------------------------------

        left_width = 6.00

        right_width = (
            width - left_width
        )

        # ------------------------------------------------------
        # Horizontal bands
        #
        # +-------------------------+
        # | Living       | Kitchen  |
        # |              |          |
        # +--------------+----------+
        # | Master       | Bedroom2 |
        # |              |          |
        # |              +----------+
        # |              | Toilets  |
        # +--------------+----------+
        # | Foyer        | Utility  |
        # +-------------------------+
        #
        # All coordinates are constructed from the
        # boundaries, so no room can extend beyond the unit.
        # ------------------------------------------------------

        living_height = max(
            2.90,
            depth * 0.31,
        )

        lower_height = max(
            1.80,
            depth * 0.18,
        )

        middle_height = (
            depth
            - living_height
            - lower_height
        )

        if middle_height < 3.50:

            middle_height = 3.50

            lower_height = (
                depth
                - living_height
                - middle_height
            )

        # ------------------------------------------------------
        # Y coordinates
        # ------------------------------------------------------

        y_lower = 0.0

        y_middle = (
            lower_height
        )

        y_top = (
            lower_height
            + middle_height
        )

        # ------------------------------------------------------
        # Middle band split
        #
        # Master bedroom gets the complete left side.
        #
        # Right side is divided into:
        #
        # Bedroom 2
        # Attached toilet
        # Common toilet
        # ------------------------------------------------------

        bedroom2_height = middle_height * 0.58

        toilet_band_height = (
            middle_height
            - bedroom2_height
        )

        toilet_left_width = (
            right_width * 0.50
        )

        toilet_right_width = (
            right_width
            - toilet_left_width
        )

        rooms = [

            # --------------------------------------------------
            # TOP BAND
            # --------------------------------------------------

            Room(
                name="Living / Dining",
                x=0.0,
                y=y_top,
                width=left_width,
                depth=living_height,
                room_type="living",
            ),

            Room(
                name="Kitchen",
                x=left_width,
                y=y_top,
                width=right_width,
                depth=living_height,
                room_type="kitchen",
            ),

            # --------------------------------------------------
            # MIDDLE BAND
            # --------------------------------------------------

            Room(
                name="Master Bedroom",
                x=0.0,
                y=y_middle,
                width=left_width,
                depth=middle_height,
                room_type="bedroom",
            ),

            Room(
                name="Bedroom 2",
                x=left_width,
                y=y_middle + toilet_band_height,
                width=right_width,
                depth=bedroom2_height,
                room_type="bedroom",
            ),

            # --------------------------------------------------
            # TOILETS
            # --------------------------------------------------

            Room(
                name="Attached Toilet",
                x=left_width,
                y=y_middle,
                width=toilet_left_width,
                depth=toilet_band_height,
                room_type="toilet",
            ),

            Room(
                name="Common Toilet",
                x=(
                    left_width
                    + toilet_left_width
                ),
                y=y_middle,
                width=toilet_right_width,
                depth=toilet_band_height,
                room_type="toilet",
            ),

            # --------------------------------------------------
            # LOWER BAND
            # --------------------------------------------------

            Room(
                name="Foyer",
                x=0.0,
                y=y_lower,
                width=left_width,
                depth=lower_height,
                room_type="foyer",
            ),

            Room(
                name="Utility",
                x=left_width,
                y=y_lower,
                width=right_width,
                depth=lower_height,
                room_type="utility",
            ),
        ]

        # ------------------------------------------------------
        # Doors
        # ------------------------------------------------------

        doors = [

            # Living -> Master
            Door(
                x=2.40,
                y=y_top,
                width=0.90,
                orientation="horizontal",
            ),

            # Living -> Kitchen
            Door(
                x=left_width,
                y=y_top + living_height * 0.45,
                width=0.90,
                orientation="vertical",
            ),

            # Master -> Attached Toilet
            Door(
                x=left_width,
                y=y_middle + toilet_band_height * 0.65,
                width=0.75,
                orientation="vertical",
            ),

            # Common corridor/foyer -> Common Toilet
            Door(
                x=(
                    left_width
                    + toilet_left_width
                    + toilet_right_width * 0.50
                ),
                y=y_middle,
                width=0.75,
                orientation="horizontal",
            ),

            # Bedroom 2 entrance
            Door(
                x=left_width,
                y=y_middle + toilet_band_height + bedroom2_height * 0.35,
                width=0.90,
                orientation="vertical",
            ),

            # Main entrance
            Door(
                x=left_width * 0.50,
                y=0.0,
                width=1.00,
                orientation="horizontal",
            ),
        ]

        # ------------------------------------------------------
        # Windows
        # ------------------------------------------------------

        windows = [

            # Living
            Window(
                x=1.50,
                y=depth,
                width=2.00,
                orientation="north",
            ),

            # Kitchen
            Window(
                x=width,
                y=y_top + living_height * 0.45,
                width=1.50,
                orientation="east",
            ),

            # Master
            Window(
                x=0.0,
                y=y_middle + middle_height * 0.50,
                width=1.80,
                orientation="west",
            ),

            # Bedroom 2
            Window(
                x=width,
                y=y_middle + toilet_band_height + bedroom2_height * 0.45,
                width=1.80,
                orientation="east",
            ),

            # Utility
            Window(
                x=width,
                y=lower_height * 0.50,
                width=1.20,
                orientation="east",
            ),
        ]

        return UnitPlan(
            unit_id=unit_id,
            unit_type="2BHK",
            carpet_area_m2=target_area,
            width=width,
            depth=depth,
            rooms=rooms,
            doors=doors,
            windows=windows,
        )
