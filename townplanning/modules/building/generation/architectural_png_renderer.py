from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from .architectural_floor_plan import UnitPlan


class ArchitecturalPNGRenderer:

    def render(
        self,
        unit: UnitPlan,
        output: str | Path,
    ):

        output = Path(output)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fig, ax = plt.subplots(
            figsize=(12, 10)
        )

        # --------------------------------------------------
        # Draw rooms
        # --------------------------------------------------

        for room in unit.rooms:

            rectangle = Rectangle(
                (
                    room.x,
                    room.y,
                ),
                room.width,
                room.depth,
                fill=False,
                linewidth=2.0,
            )

            ax.add_patch(
                rectangle
            )

            ax.text(
                room.x +
                room.width / 2,
                room.y +
                room.depth / 2,
                (
                    f"{room.name}\n"
                    f"{room.width:.2f} × "
                    f"{room.depth:.2f} m\n"
                    f"{room.area:.1f} m²"
                ),
                ha="center",
                va="center",
                fontsize=8,
            )

        # --------------------------------------------------
        # Outer wall
        # --------------------------------------------------

        ax.add_patch(
            Rectangle(
                (0, 0),
                unit.width,
                unit.depth,
                fill=False,
                linewidth=4,
            )
        )

        # --------------------------------------------------
        # Doors
        # --------------------------------------------------

        for door in unit.doors:

            if door.orientation == "vertical":

                ax.plot(
                    [
                        door.x,
                        door.x,
                    ],
                    [
                        door.y,
                        door.y + door.width,
                    ],
                    linewidth=4,
                )

            else:

                ax.plot(
                    [
                        door.x,
                        door.x + door.width,
                    ],
                    [
                        door.y,
                        door.y,
                    ],
                    linewidth=4,
                )

        # --------------------------------------------------
        # Windows
        # --------------------------------------------------

        for window in unit.windows:

            if window.orientation == "north":

                ax.plot(
                    [
                        window.x,
                        window.x + window.width,
                    ],
                    [
                        unit.depth,
                        unit.depth,
                    ],
                    linewidth=5,
                )

            elif window.orientation == "south":

                ax.plot(
                    [
                        window.x,
                        window.x + window.width,
                    ],
                    [
                        0,
                        0,
                    ],
                    linewidth=5,
                )

            elif window.orientation == "east":

                ax.plot(
                    [
                        unit.width,
                        unit.width,
                    ],
                    [
                        window.y,
                        window.y + window.width,
                    ],
                    linewidth=5,
                )

            elif window.orientation == "west":

                ax.plot(
                    [
                        0,
                        0,
                    ],
                    [
                        window.y,
                        window.y + window.width,
                    ],
                    linewidth=5,
                )

        # --------------------------------------------------
        # Annotation
        # --------------------------------------------------

        ax.text(
            unit.width / 2,
            unit.depth + 0.5,
            (
                f"{unit.unit_id}  "
                f"{unit.unit_type}  |  "
                f"Carpet Area: "
                f"{unit.carpet_area_m2:.1f} m²"
            ),
            ha="center",
            fontsize=12,
        )

        ax.set_aspect(
            "equal",
            adjustable="box",
        )

        ax.set_xlim(
            -0.5,
            unit.width + 0.5,
        )

        ax.set_ylim(
            -0.5,
            unit.depth + 1.0,
        )

        ax.set_xlabel(
            "Meters"
        )

        ax.set_ylabel(
            "Meters"
        )

        ax.grid(
            True,
            linewidth=0.3,
        )

        fig.tight_layout()

        fig.savefig(
            output,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close(fig)

        return output