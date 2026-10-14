from __future__ import annotations

from itertools import combinations

from shapely.geometry import box

from .architectural_floor_plan import UnitPlan


class ArchitecturalValidator:

    def validate(
        self,
        unit: UnitPlan,
    ):

        errors = []

        unit_polygon = box(
            0,
            0,
            unit.width,
            unit.depth,
        )

        polygons = []

        for room in unit.rooms:

            if room.width <= 0:
                errors.append(
                    f"{room.name}: invalid width"
                )

            if room.depth <= 0:
                errors.append(
                    f"{room.name}: invalid depth"
                )

            polygon = box(
                room.x,
                room.y,
                room.x + room.width,
                room.y + room.depth,
            )

            polygons.append(
                (room, polygon)
            )

            # ----------------------------------------------
            # Room must remain inside apartment
            # ----------------------------------------------

            if not unit_polygon.covers(
                polygon
            ):
                errors.append(
                    f"{room.name}: outside unit"
                )

        # --------------------------------------------------
        # Detect overlapping rooms
        # --------------------------------------------------

        for (
            first,
            second,
        ) in combinations(
            polygons,
            2,
        ):

            room_a, polygon_a = first
            room_b, polygon_b = second

            intersection = (
                polygon_a.intersection(
                    polygon_b
                )
            )

            # Shared wall is OK.
            #
            # Actual overlapping area is NOT.
            if intersection.area > 0.001:

                errors.append(
                    f"OVERLAP: "
                    f"{room_a.name} / "
                    f"{room_b.name}"
                )

        # --------------------------------------------------
        # Check rooms are connected to another room
        # --------------------------------------------------

        for room, polygon in polygons:

            connected = False

            for other, other_polygon in polygons:

                if room is other:
                    continue

                touching = (
                    polygon.boundary.intersection(
                        other_polygon.boundary
                    )
                )

                if not touching.is_empty:

                    connected = True
                    break

            if not connected:

                errors.append(
                    f"VOID/FLOATING ROOM: "
                    f"{room.name}"
                )

        if errors:

            raise ValueError(
                "Architectural plan validation failed:\n"
                + "\n".join(
                    f" - {error}"
                    for error in errors
                )
            )

        return True