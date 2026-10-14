"""
Architectural presentation renderer for the existing ActualBuildingPlanGenerator.

Purpose
-------
Keep the existing deterministic geometry/FSI logic, but replace the plain
engineering-style PNG/DXF export with an architectural presentation style:

- thick external/internal wall graphics
- doors with swing arcs
- windows
- balconies
- room names + dimensions + areas
- simple furniture symbols
- kitchen/bath fixtures
- dimension strings
- north arrow and title block
- real DXF entities on separate CAD layers

Usage
-----
Put this file beside actual_plan_generator.py and change the application import:

    from townplanning.modules.building.generation.architectural_style_plan_generator \
        import ArchitecturalStyleBuildingPlanGenerator

Then use:

    generator = ArchitecturalStyleBuildingPlanGenerator(output_dir="...")

The inherited generate() method still performs the existing geometry,
validation and report generation; this class only replaces the presentation
exporters.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import ezdxf
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Rectangle

from .actual_plan_generator import ActualBuildingPlanGenerator, Building, Room, Unit


class ArchitecturalStyleBuildingPlanGenerator(ActualBuildingPlanGenerator):
    """
    Presentation-oriented subclass of ActualBuildingPlanGenerator.

    The geometry remains deterministic. This class is deliberately kept
    separate so the architectural renderer can evolve without changing the
    FSI/building solver.
    """

    WALL_OUTER = 0.22
    WALL_INNER = 0.12

    # ------------------------------------------------------------------
    # PUBLIC EXPORT OVERRIDES
    # ------------------------------------------------------------------

    def export_floor_plans(self, site) -> None:
        for building in site.buildings:
            for floor in range(1, building.floors + 1):
                png_path = self.output_dir / (
                    f"{building.building_id}_floor_{floor:02d}.png"
                )
                dxf_path = self.output_dir / (
                    f"{building.building_id}_floor_{floor:02d}.dxf"
                )

                self._export_arch_floor_png(building, png_path, floor)
                self._export_arch_floor_dxf(building, dxf_path, floor)

    def export_units(self, site) -> None:
        for building in site.buildings:
            for unit in building.units:
                png_path = self.output_dir / (
                    f"{unit.unit_id}_{unit.unit_type}.png"
                )
                dxf_path = self.output_dir / (
                    f"{unit.unit_id}_{unit.unit_type}.dxf"
                )

                self._export_arch_unit_png(unit, png_path)
                self._export_arch_unit_dxf(unit, dxf_path)

    # ------------------------------------------------------------------
    # COMMON DRAWING HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _room_color(room_type: str):
        # Deliberately light, neutral architectural presentation.
        # Matplotlib chooses the final rendering appearance.
        colors = {
            "living": "#F4F0E8",
            "bedroom": "#F7F3ED",
            "kitchen": "#EEEAE2",
            "toilet": "#E9E9E9",
            "utility": "#EFECE6",
            "corridor": "#F2F2EF",
            "lift": "#E7E7E7",
            "staircase": "#EAEAEA",
            "lobby": "#F0F0EC",
        }
        return colors.get(room_type, "#F7F5F0")

    @staticmethod
    def _safe_text(text: str) -> str:
        return str(text).replace("_", " ")

    @staticmethod
    def _fmt_dim(value: float) -> str:
        """Metric architectural dimension, with feet/inches avoided in CAD."""
        return f"{value:.2f} m"

    def _draw_room_fill(self, ax: Any, room: Room) -> None:
        ax.add_patch(
            Rectangle(
                (room.x, room.y),
                room.width,
                room.depth,
                facecolor=self._room_color(room.room_type),
                edgecolor="none",
                zorder=1,
            )
        )

    def _draw_room_label(self, ax, room: Room, compact: bool = False) -> None:
        """Draw a room label away from the main furniture/fixture zone."""
        name = self._safe_text(room.name)
        if compact:
            label = name
        else:
            label = (f"{name}\n" f"{room.width:.2f} × {room.depth:.2f} m\n" f"{room.area:.1f} m²")

        tx, ty = self._room_label_anchor(room)
        fontsize = self._room_label_fontsize(room)

        ax.text(tx, ty, label, ha="center", va="center",
                fontsize=fontsize if not compact else max(4.5, fontsize - 0.4),
                zorder=25,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.82, pad=0.8))

    def _draw_room_boundary(self, ax: Any, room: Room) -> None:
        ax.add_patch(
            Rectangle(
                (room.x, room.y),
                room.width,
                room.depth,
                fill=False,
                linewidth=1.0,
                zorder=5,
            )
        )

    def _draw_door_png(
        self,
        ax: Any,
        x: float,
        y: float,
        width: float = 0.90,
        orientation: str = "horizontal",
    ) -> None:
        """
        Draw a conventional hinged door symbol.

        x/y is the hinge-side reference on the wall.
        """
        r = width

        if orientation == "horizontal":
            # Leaf opens upward from a horizontal wall.
            ax.plot([x, x], [y, y + r], linewidth=1.0, color="black", zorder=15)
            ax.add_patch(
                Arc(
                    (x, y),
                    2 * r,
                    2 * r,
                    theta1=0,
                    theta2=90,
                    linewidth=0.8,
                    fill=False,
                    zorder=14,
                )
            )
        else:
            ax.plot([x, x + r], [y, y], linewidth=1.0, color="black", zorder=15)
            ax.add_patch(
                Arc(
                    (x, y),
                    2 * r,
                    2 * r,
                    theta1=0,
                    theta2=90,
                    linewidth=0.8,
                    fill=False,
                    zorder=14,
                )
            )

    def _draw_window_png(
        self,
        ax: Any,
        x: float,
        y: float,
        width: float,
        orientation: str = "horizontal",
    ) -> None:
        gap = 0.08
        if orientation == "horizontal":
            ax.plot(
                [x - width / 2, x + width / 2],
                [y, y],
                linewidth=4.0,
                color="black",
                solid_capstyle="butt",
                zorder=16,
            )
            ax.plot(
                [x - width / 2, x + width / 2],
                [y + gap, y + gap],
                linewidth=0.8,
                color="black",
                zorder=17,
            )
        else:
            ax.plot(
                [x, x],
                [y - width / 2, y + width / 2],
                linewidth=4.0,
                color="black",
                solid_capstyle="butt",
                zorder=16,
            )


    def _room_label_fontsize(self, room: Room) -> float:
        """Adaptive architectural text size for room labels."""
        area = room.width * room.depth
        min_side = min(room.width, room.depth)
        if room.room_type == "toilet":
            if min_side < 1.50:
                return 3.8
            if area < 4.0:
                return 4.2
            return 4.7
        if room.room_type == "utility":
            return 4.0 if min_side < 1.50 else 4.6
        if area < 8.0:
            return 4.8
        if area < 13.0:
            return 5.3
        if area < 20.0:
            return 5.8
        return 6.2

    # ------------------------------------------------------------------
    # FURNITURE / FIXTURES
    # ------------------------------------------------------------------

    def _draw_bed(self, ax, x, y, w, d) -> None:
        """Draw a clean architectural bed symbol."""
        ax.add_patch(Rectangle((x, y), w, d, facecolor="white",
                               edgecolor="black", linewidth=0.9, zorder=20))
        head_h = min(0.35, d * 0.16)
        ax.add_patch(Rectangle((x, y + d - head_h), w, head_h,
                               fill=False, linewidth=0.9, zorder=21))
        pillow_gap = 0.08
        pillow_w = max(0.25, (w - 0.24 - pillow_gap) / 2)
        pillow_h = min(0.42, d * 0.12)
        for i in range(2):
            px = x + 0.08 + i * (pillow_w + pillow_gap)
            py = y + d - head_h - pillow_h - 0.05
            ax.add_patch(Rectangle((px, py), pillow_w, pillow_h,
                                   fill=False, linewidth=0.55, zorder=22))
        ax.plot([x + w * 0.50, x + w * 0.50],
                [y + 0.04, y + d - head_h],
                linewidth=0.35, color="black", zorder=21)

    def _place_bed_against_wall(self, room: Room):
        """Return bed geometry with its headboard touching the upper wall."""
        bw = min(room.width * 0.52, 1.80)
        bd = min(room.depth * 0.55, 2.10)
        if bw <= 0.8 or bd <= 1.0:
            return None
        x = room.x + (room.width - bw) / 2
        y = room.y + room.depth - bd
        return x, y, bw, bd

    def _draw_sofa(self, ax, x, y, w, d) -> None:
        ax.add_patch(Rectangle((x, y), w, d, fill=False, linewidth=0.9, zorder=20))
        ax.add_patch(
            Rectangle(
                (x + 0.08, y + d * 0.45),
                w - 0.16,
                d * 0.45,
                fill=False,
                linewidth=0.6,
                zorder=21,
            )
        )

    def _draw_dining_table(self, ax, x, y, w=1.2, d=0.9) -> None:
        ax.add_patch(Rectangle((x, y), w, d, fill=False, linewidth=0.9, zorder=20))
        for px, py in (
            (x + w / 2, y - 0.22),
            (x + w / 2, y + d + 0.22),
            (x - 0.22, y + d / 2),
            (x + w + 0.22, y + d / 2),
        ):
            ax.add_patch(Circle((px, py), 0.11, fill=False, linewidth=0.6, color="black", zorder=21))

    def _draw_tv(self, ax, x, y, w=1.4) -> None:
        ax.plot([x - w / 2, x + w / 2], [y, y], linewidth=2.0, color="black", zorder=20)
        ax.plot(
            [x - w / 2, x + w / 2],
            [y + 0.08, y + 0.08],
            linewidth=0.6,
            zorder=21,
        )

    def _draw_kitchen(self, ax, room: Room) -> None:
        # Counter run along one wall.
        counter = min(0.65, room.depth * 0.28)
        ax.add_patch(
            Rectangle(
                (room.x + 0.10, room.y + room.depth - counter - 0.10),
                max(0.6, room.width - 0.20),
                counter,
                fill=False,
                linewidth=1.0,
                zorder=20,
            )
        )
        # Sink + hob.
        if room.width > 1.5:
            ax.add_patch(
                Circle(
                    (room.x + room.width * 0.35, room.y + room.depth - counter / 2 - 0.10),
                    0.14,
                    fill=False,
                    linewidth=0.6,
                    zorder=21,
                )
            )
            ax.add_patch(
                Circle(
                    (room.x + room.width * 0.68, room.y + room.depth - counter / 2 - 0.10),
                    0.11,
                    fill=False,
                    linewidth=0.6,
                    zorder=21,
                )
            )

    def _draw_bathroom(self, ax, room: Room) -> None:
        # WC.
        cx = room.x + room.width * 0.72
        cy = room.y + room.depth * 0.30
        ax.add_patch(
            Rectangle(
                (cx - 0.22, cy - 0.30),
                0.44,
                0.60,
                fill=False,
                linewidth=0.7,
                zorder=20,
            )
        )
        # Wash basin.
        ax.add_patch(
            Circle(
                (room.x + room.width * 0.25, room.y + room.depth * 0.68),
                0.18,
                fill=False,
                linewidth=0.7,
                zorder=20,
            )
        )
        # Shower.
        ax.add_patch(
            Rectangle(
                (room.x + 0.10, room.y + 0.10),
                max(0.65, room.width * 0.32),
                max(0.65, room.depth * 0.28),
                fill=False,
                linewidth=0.7,
                zorder=20,
            )
        )

    def _place_bed_against_wall(self, room: Room):
        """
        Returns x, y, width, depth for a bedroom bed.

        The bed is positioned against the upper wall of the room,
        leaving a small graphic clearance.
        """
    
        bw = min(room.width * 0.52, 1.80)
        bd = min(room.depth * 0.55, 2.10)
    
        if bw <= 0.8 or bd <= 1.0:
            return None
    
        clearance = 0.08
    
        x = room.x + (room.width - bw) / 2
        y = room.y + room.depth - bd - clearance
    
        return x, y, bw, bd

    def _draw_room_furniture(self, ax, room: Room) -> None:
        rt = room.room_type

        if rt == "bedroom":
            placement = self._place_bed_against_wall(room)
            if placement:
                self._draw_bed(ax, *placement)

        elif rt == "living":
            sw = min(room.width * 0.42, 2.4)
            sd = min(room.depth * 0.24, 0.8)
            self._draw_sofa(
                ax,
                room.x + 0.20,
                room.y + room.depth * 0.52,
                sw,
                max(0.45, sd),
            )
            if room.width > 2.8 and room.depth > 2.5:
                self._draw_dining_table(
                    ax,
                    room.x + room.width * 0.58,
                    room.y + room.depth * 0.30,
                    min(1.2, room.width * 0.22),
                    min(0.9, room.depth * 0.22),
                )
                self._draw_tv(
                    ax,
                    room.x + room.width * 0.82,
                    room.y + room.depth * 0.75,
                    min(1.3, room.width * 0.25),
                )

        elif rt == "kitchen":
            self._draw_kitchen(ax, room)

        elif rt == "toilet":
            self._draw_bathroom(ax, room)

        elif rt == "staircase":
            # Stair treads.
            n = 7
            usable_h = max(1.0, room.depth - 0.2)
            for i in range(n):
                yy = room.y + 0.10 + usable_h * i / n
                ax.plot(
                    [room.x + 0.10, room.x + room.width - 0.10],
                    [yy, yy],
                    linewidth=0.6,
                    zorder=20,
                )

    # ------------------------------------------------------------------
    # BALCONY
    # ------------------------------------------------------------------

    def _balcony_rect(self, unit: Unit):
        """
        Adds a presentation balcony to the external/top side of the unit.
        This is a graphical architectural feature; it is not included in
        the existing FSI geometry.
        """
        width = unit.width
        depth = min(1.50, max(1.00, unit.depth * 0.10))
        return unit.x, unit.y + unit.depth, width, depth

    def _draw_balcony_png(self, ax, unit: Unit) -> None:
        x, y, w, d = self._balcony_rect(unit)
        ax.add_patch(
            Rectangle(
                (x, y),
                w,
                d,
                facecolor="#EEEAE2",
                edgecolor="black",
                linewidth=1.0,
                zorder=2,
            )
        )
        # Railing.
        ax.plot([x, x + w], [y + d, y + d], linewidth=2.0, zorder=18)
        # Small chairs/table where space permits.
        if w > 2.5:
            cx = x + w * 0.50
            cy = y + d * 0.50
            ax.add_patch(Circle((cx, cy), 0.20, fill=False, linewidth=0.7, zorder=20))
            ax.add_patch(Circle((cx - 0.55, cy), 0.18, fill=False, linewidth=0.7, zorder=20))
            ax.add_patch(Circle((cx + 0.55, cy), 0.18, fill=False, linewidth=0.7, zorder=20))

        ax.text(
            x + w / 2,
            y + d / 2,
            "BALCONY",
            ha="center",
            va="center",
            fontsize=5.5,
            zorder=21,
        )

    # ------------------------------------------------------------------
    # DIMENSIONS
    # ------------------------------------------------------------------

    def _dimension_png(self, ax, x1, y1, x2, y2, offset=0.7, text=None):
        dx = x2 - x1
        dy = y2 - y1

        if abs(dy) < 1e-9:
            yy = y1 + offset
            ax.annotate(
                "",
                xy=(x2, yy),
                xytext=(x1, yy),
                arrowprops={"arrowstyle": "<->", "linewidth": 0.6},
            )
            label = text or self._fmt_dim(abs(dx))
            ax.text((x1 + x2) / 2, yy + 0.12, label, ha="center", va="bottom", fontsize=5.5)
        elif abs(dx) < 1e-9:
            xx = x1 + offset
            ax.annotate(
                "",
                xy=(xx, y2),
                xytext=(xx, y1),
                arrowprops={"arrowstyle": "<->", "linewidth": 0.6},
            )
            label = text or self._fmt_dim(abs(dy))
            ax.text(
                xx + 0.12,
                (y1 + y2) / 2,
                label,
                ha="left",
                va="center",
                rotation=90,
                fontsize=5.5,
            )

    # ------------------------------------------------------------------
    # FLOOR PNG
    # ------------------------------------------------------------------

    def _export_arch_floor_png(self, building: Building, path: Path, floor: int) -> None:
        fig, ax = plt.subplots(figsize=(14, 11))

        # Room fills first.
        for room in building.common_spaces:
            self._draw_room_fill(ax, room)

        for unit in building.units:
            for room in unit.rooms:
                self._draw_room_fill(ax, room)

        # Balconies.
        for unit in building.units:
            self._draw_balcony_png(ax, unit)

        # Room boundaries + furniture.
        for room in building.common_spaces:
            self._draw_room_boundary(ax, room)
            self._draw_room_label(ax, room, compact=True)
            self._draw_room_furniture(ax, room)

        for unit in building.units:
            ax.add_patch(
                Rectangle(
                    (unit.x, unit.y),
                    unit.width,
                    unit.depth,
                    fill=False,
                    linewidth=2.2,
                    zorder=7,
                )
            )

            for room in unit.rooms:
                self._draw_room_boundary(ax, room)
                self._draw_room_label(ax, room)
                self._draw_room_furniture(ax, room)

            # Unit title outside the room area so it cannot collide with
            # furniture or room labels.
            ax.text(
                unit.x + unit.width / 2,
                unit.y + unit.depth + 0.22,
                f"{unit.unit_id}  {unit.unit_type}",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
                zorder=26,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, pad=0.8),
            )

            # Doors/windows.
            for door in unit.doors:
                self._draw_door_png(
                    ax,
                    door.x,
                    door.y,
                    door.width,
                    door.orientation,
                )

            for window in unit.windows:
                self._draw_window_png(
                    ax,
                    window.x,
                    window.y,
                    window.width,
                    window.orientation,
                )

        # External building wall.
        ax.add_patch(
            Rectangle(
                (building.x, building.y),
                building.width,
                building.depth,
                fill=False,
                linewidth=3.0,
                zorder=30,
            )
        )

        # Overall dimensions.
        self._dimension_png(
            ax,
            building.x,
            building.y,
            building.x + building.width,
            building.y,
            offset=-1.0,
        )
        self._dimension_png(
            ax,
            building.x,
            building.y,
            building.x,
            building.y + building.depth,
            offset=-1.0,
        )

        # North arrow.
        nx = building.x + building.width * 0.92
        ny = building.y + building.depth * 0.84
        ax.annotate(
            "N",
            xy=(nx, ny + 2.0),
            xytext=(nx, ny),
            ha="center",
            fontsize=14,
            arrowprops={"arrowstyle": "->", "linewidth": 1.2},
        )

        # Title block.
        ax.text(
            building.x,
            building.y + building.depth + 1.8,
            f"{building.building_id} — FLOOR {floor} RESIDENTIAL FLOOR PLAN",
            fontsize=13,
            fontweight="bold",
            ha="left",
        )
        ax.text(
            building.x,
            building.y + building.depth + 1.2,
            f"Conceptual Architectural Presentation  |  {building.width:.2f} × {building.depth:.2f} m",
            fontsize=7,
            ha="left",
        )

        # Legend.
        legend_x = building.x
        legend_y = building.y - 2.4
        ax.text(legend_x, legend_y, "LEGEND", fontsize=8, fontweight="bold")
        ax.text(
            legend_x,
            legend_y - 0.45,
            "Bedroom • Living / Dining • Kitchen • Toilet / Bath • Balcony • Core",
            fontsize=6.5,
        )

        margin = 3.0
        ax.set_xlim(
            building.x - margin,
            building.x + building.width + margin,
        )
        ax.set_ylim(
            building.y - margin,
            building.y + building.depth + margin + 2.0,
        )
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")

        fig.savefig(path, dpi=220, bbox_inches="tight")
        plt.close(fig)

    # ------------------------------------------------------------------
    # UNIT PNG
    # ------------------------------------------------------------------

    def _export_arch_unit_png(self, unit: Unit, path: Path) -> None:
        fig, ax = plt.subplots(figsize=(11, 9))

        for room in unit.rooms:
            self._draw_room_fill(ax, room)

        self._draw_balcony_png(ax, unit)

        for room in unit.rooms:
            self._draw_room_boundary(ax, room)
            self._draw_room_label(ax, room)
            self._draw_room_furniture(ax, room)

        ax.add_patch(
            Rectangle(
                (unit.x, unit.y),
                unit.width,
                unit.depth,
                fill=False,
                linewidth=3.0,
                zorder=30,
            )
        )

        for door in unit.doors:
            self._draw_door_png(ax, door.x, door.y, door.width, door.orientation)

        for window in unit.windows:
            self._draw_window_png(
                ax,
                window.x,
                window.y,
                window.width,
                window.orientation,
            )

        self._dimension_png(
            ax,
            unit.x,
            unit.y,
            unit.x + unit.width,
            unit.y,
            offset=-0.9,
        )
        self._dimension_png(
            ax,
            unit.x,
            unit.y,
            unit.x,
            unit.y + unit.depth,
            offset=-0.9,
        )

        ax.text(
            unit.x,
            unit.y + unit.depth + 1.3,
            f"{unit.unit_id} — {unit.unit_type} APARTMENT",
            fontsize=13,
            fontweight="bold",
        )
        ax.text(
            unit.x,
            unit.y + unit.depth + 0.75,
            f"Approx. Unit Area: {unit.area:.1f} m²",
            fontsize=8,
        )

        margin = 2.4
        ax.set_xlim(unit.x - margin, unit.x + unit.width + margin)
        ax.set_ylim(unit.y - margin, unit.y + unit.depth + margin + 1.5)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")

        fig.savefig(path, dpi=220, bbox_inches="tight")
        plt.close(fig)

    # ------------------------------------------------------------------
    # DXF LAYERS
    # ------------------------------------------------------------------

    def _new_arch_dxf(self):
        doc = ezdxf.new("R2013")
        msp = doc.modelspace()

        layers = {
            "A-WALL": 7,
            "A-WALL-THICK": 7,
            "A-ROOM": 8,
            "A-DOOR": 3,
            "A-WINDOW": 4,
            "A-FURN": 6,
            "A-FIXTURE": 5,
            "A-TEXT": 2,
            "A-DIMS": 1,
            "A-BALCONY": 4,
            "A-CORE": 9,
            "A-SITE": 7,
        }

        for name, color in layers.items():
            if name not in doc.layers:
                doc.layers.new(name=name, dxfattribs={"color": color})

        return doc, msp

    def _dxf_rect(self, msp, x, y, w, d, layer="A-WALL"):
        msp.add_lwpolyline(
            [
                (x, y),
                (x + w, y),
                (x + w, y + d),
                (x, y + d),
                (x, y),
            ],
            close=True,
            dxfattribs={"layer": layer},
        )

    def _dxf_text(self, msp, text, x, y, height=0.20, layer="A-TEXT"):
        e = msp.add_text(
            str(text),
            dxfattribs={
                "height": height,
                "layer": layer,
            },
        )
        e.dxf.insert = (x, y)

    def _dxf_line(self, msp, p1, p2, layer):
        msp.add_line(p1, p2, dxfattribs={"layer": layer})

    def _dxf_arc(self, msp, center, radius, start_angle, end_angle, layer="A-DOOR"):
        msp.add_arc(
            center,
            radius,
            start_angle,
            end_angle,
            dxfattribs={"layer": layer},
        )

    def _dxf_circle(self, msp, center, radius, layer="A-FURN"):
        msp.add_circle(center, radius, dxfattribs={"layer": layer})

    def _dxf_door(self, msp, x, y, width=0.90, orientation="horizontal"):
        if orientation == "horizontal":
            self._dxf_line(
                msp,
                (x, y),
                (x, y + width),
                "A-DOOR",
            )
            self._dxf_arc(
                msp,
                (x, y),
                width,
                0,
                90,
            )
        else:
            self._dxf_line(
                msp,
                (x, y),
                (x + width, y),
                "A-DOOR",
            )
            self._dxf_arc(
                msp,
                (x, y),
                width,
                0,
                90,
            )

    def _dxf_window(self, msp, x, y, width, orientation="horizontal"):
        if orientation == "horizontal":
            self._dxf_line(
                msp,
                (x - width / 2, y),
                (x + width / 2, y),
                "A-WINDOW",
            )
            self._dxf_line(
                msp,
                (x - width / 2, y + 0.08),
                (x + width / 2, y + 0.08),
                "A-WINDOW",
            )
        else:
            self._dxf_line(
                msp,
                (x, y - width / 2),
                (x, y + width / 2),
                "A-WINDOW",
            )

    def _dxf_bed(self, msp, x, y, w, d):
        self._dxf_rect(msp, x, y, w, d, "A-FURN")
        head_h = min(0.35, d * 0.16)
        self._dxf_rect(msp, x, y + d - head_h, w, head_h, "A-FURN")
        pillow_gap = 0.08
        pillow_w = max(0.25, (w - 0.24 - pillow_gap) / 2)
        pillow_h = min(0.42, d * 0.12)
        for i in range(2):
            px = x + 0.08 + i * (pillow_w + pillow_gap)
            py = y + d - head_h - pillow_h - 0.05
            self._dxf_rect(msp, px, py, pillow_w, pillow_h, "A-FURN")
        self._dxf_line(msp, (x + w * 0.50, y + 0.04),
                       (x + w * 0.50, y + d - head_h), "A-FURN")

    def _dxf_sofa(self, msp, x, y, w, d):
        self._dxf_rect(msp, x, y, w, d, "A-FURN")
        self._dxf_rect(msp, x + 0.08, y + d * 0.45, w - 0.16, d * 0.45, "A-FURN")

    def _room_label_anchor(self, room: Room):
        if room.room_type == "bedroom":
            return room.x + room.width * 0.50, room.y + room.depth * 0.25
        if room.room_type == "living":
            return room.x + room.width * 0.48, room.y + room.depth * 0.76
        if room.room_type == "kitchen":
            return room.x + room.width * 0.50, room.y + room.depth * 0.48
        if room.room_type == "toilet":
            return room.x + room.width * 0.50, room.y + room.depth * 0.52
        if room.room_type == "utility":
            return room.x + room.width * 0.50, room.y + room.depth * 0.50
        return room.x + room.width * 0.50, room.y + room.depth * 0.50

    def _dxf_label_height(self, room: Room) -> float:
        if room.room_type == "toilet":
            return 0.10
        if room.room_type == "utility":
            return 0.11
        return 0.14

    def _dxf_furniture(self, msp, room: Room):
        rt = room.room_type

        if rt == "bedroom":
            placement = self._place_bed_against_wall(room)
            if placement:
                self._dxf_bed(msp, *placement)

        elif rt == "living":
            sw = min(room.width * 0.42, 2.4)
            sd = max(0.45, min(room.depth * 0.24, 0.8))
            self._dxf_sofa(
                msp,
                room.x + 0.20,
                room.y + room.depth * 0.52,
                sw,
                sd,
            )

            if room.width > 2.8 and room.depth > 2.5:
                tw = min(1.2, room.width * 0.22)
                td = min(0.9, room.depth * 0.22)
                tx = room.x + room.width * 0.58
                ty = room.y + room.depth * 0.30
                self._dxf_rect(msp, tx, ty, tw, td, "A-FURN")
                for px, py in (
                    (tx + tw / 2, ty - 0.22),
                    (tx + tw / 2, ty + td + 0.22),
                    (tx - 0.22, ty + td / 2),
                    (tx + tw + 0.22, ty + td / 2),
                ):
                    self._dxf_circle(msp, (px, py), 0.11)

        elif rt == "kitchen":
            counter = min(0.65, room.depth * 0.28)
            self._dxf_rect(
                msp,
                room.x + 0.10,
                room.y + room.depth - counter - 0.10,
                max(0.6, room.width - 0.20),
                counter,
                "A-FIXTURE",
            )

        elif rt == "toilet":
            cx = room.x + room.width * 0.72
            cy = room.y + room.depth * 0.30
            self._dxf_rect(msp, cx - 0.22, cy - 0.30, 0.44, 0.60, "A-FIXTURE")
            self._dxf_circle(
                msp,
                (room.x + room.width * 0.25, room.y + room.depth * 0.68),
                0.18,
                "A-FIXTURE",
            )

        elif rt == "staircase":
            n = 7
            usable_h = max(1.0, room.depth - 0.2)
            for i in range(n):
                yy = room.y + 0.10 + usable_h * i / n
                self._dxf_line(
                    msp,
                    (room.x + 0.10, yy),
                    (room.x + room.width - 0.10, yy),
                    "A-CORE",
                )

    def _dxf_balcony(self, msp, unit: Unit):
        x, y, w, d = self._balcony_rect(unit)
        self._dxf_rect(msp, x, y, w, d, "A-BALCONY")
        self._dxf_line(msp, (x, y + d), (x + w, y + d), "A-BALCONY")

    def _dxf_dimension(self, msp, x1, y1, x2, y2, offset=0.7, text=None):
        """
        Lightweight CAD dimension graphics. We intentionally use LINE + TEXT
        rather than DIM entities so the output remains readable in older CAD.
        """
        if abs(y2 - y1) < 1e-9:
            yy = y1 + offset
            self._dxf_line(msp, (x1, yy), (x2, yy), "A-DIMS")
            self._dxf_line(msp, (x1, yy - 0.12), (x1, yy + 0.12), "A-DIMS")
            self._dxf_line(msp, (x2, yy - 0.12), (x2, yy + 0.12), "A-DIMS")
            self._dxf_text(
                msp,
                text or self._fmt_dim(abs(x2 - x1)),
                (x1 + x2) / 2,
                yy + 0.12,
                0.16,
                "A-DIMS",
            )
        elif abs(x2 - x1) < 1e-9:
            xx = x1 + offset
            self._dxf_line(msp, (xx, y1), (xx, y2), "A-DIMS")
            self._dxf_line(msp, (xx - 0.12, y1), (xx + 0.12, y1), "A-DIMS")
            self._dxf_line(msp, (xx - 0.12, y2), (xx + 0.12, y2), "A-DIMS")
            self._dxf_text(
                msp,
                text or self._fmt_dim(abs(y2 - y1)),
                xx + 0.12,
                (y1 + y2) / 2,
                0.16,
                "A-DIMS",
            )

    # ------------------------------------------------------------------
    # FLOOR DXF
    # ------------------------------------------------------------------

    def _export_arch_floor_dxf(self, building: Building, path: Path, floor: int) -> None:
        doc, msp = self._new_arch_dxf()

        # Room fills are not required in DXF; CAD stays clean.
        self._dxf_rect(
            msp,
            building.x,
            building.y,
            building.width,
            building.depth,
            "A-WALL-THICK",
        )

        for room in building.common_spaces:
            layer = (
                "A-CORE"
                if room.room_type in {"lift", "staircase", "lobby"}
                else "A-ROOM"
            )
            self._dxf_rect(
                msp,
                room.x,
                room.y,
                room.width,
                room.depth,
                layer,
            )
            self._dxf_text(
                msp,
                room.name,
                room.x + room.width / 2,
                room.y + room.depth / 2,
                0.16,
            )
            self._dxf_furniture(msp, room)

        for unit in building.units:
            self._dxf_rect(
                msp,
                unit.x,
                unit.y,
                unit.width,
                unit.depth,
                "A-WALL",
            )
            self._dxf_text(
                msp,
                f"{unit.unit_id} {unit.unit_type}",
                unit.x + unit.width / 2,
                unit.y + unit.depth - 0.35,
                0.20,
            )

            self._dxf_balcony(msp, unit)

            for room in unit.rooms:
                self._dxf_rect(
                    msp,
                    room.x,
                    room.y,
                    room.width,
                    room.depth,
                    "A-ROOM",
                )
                label_x, label_y = self._room_label_anchor(room)
                self._dxf_text(msp, room.name, label_x, label_y,
                               self._dxf_label_height(room))
                label_x, label_y = self._room_label_anchor(room)
                self._dxf_text(
                    msp,
                    f"{room.width:.2f} x {room.depth:.2f} m",
                    label_x, label_y - 0.22,
                    0.10 if room.room_type in {"toilet", "utility"} else 0.11,
                )
                self._dxf_furniture(msp, room)

            for door in unit.doors:
                self._dxf_door(
                    msp,
                    door.x,
                    door.y,
                    door.width,
                    door.orientation,
                )

            for window in unit.windows:
                self._dxf_window(
                    msp,
                    window.x,
                    window.y,
                    window.width,
                    window.orientation,
                )

        # Overall dimensions.
        self._dxf_dimension(
            msp,
            building.x,
            building.y,
            building.x + building.width,
            building.y,
            offset=-1.0,
        )
        self._dxf_dimension(
            msp,
            building.x,
            building.y,
            building.x,
            building.y + building.depth,
            offset=-1.0,
        )

        self._dxf_text(
            msp,
            f"{building.building_id} - FLOOR {floor} RESIDENTIAL FLOOR PLAN",
            building.x,
            building.y + building.depth + 1.6,
            0.28,
        )

        # North arrow.
        nx = building.x + building.width * 0.92
        ny = building.y + building.depth * 0.84
        self._dxf_line(msp, (nx, ny), (nx, ny + 1.8), "A-DIMS")
        self._dxf_text(msp, "N", nx, ny + 2.0, 0.25, "A-DIMS")

        doc.saveas(path)

    # ------------------------------------------------------------------
    # UNIT DXF
    # ------------------------------------------------------------------

    def _export_arch_unit_dxf(self, unit: Unit, path: Path) -> None:
        doc, msp = self._new_arch_dxf()

        self._dxf_rect(
            msp,
            unit.x,
            unit.y,
            unit.width,
            unit.depth,
            "A-WALL-THICK",
        )
        self._dxf_balcony(msp, unit)

        self._dxf_text(
            msp,
            f"{unit.unit_id} {unit.unit_type} APARTMENT",
            unit.x,
            unit.y + unit.depth + 1.0,
            0.25,
        )

        for room in unit.rooms:
            self._dxf_rect(
                msp,
                room.x,
                room.y,
                room.width,
                room.depth,
                "A-ROOM",
            )
            self._dxf_text(
                msp,
                room.name,
                room.x + room.width / 2,
                room.y + room.depth / 2,
                0.18,
            )
            self._dxf_text(
                msp,
                f"{room.width:.2f} x {room.depth:.2f} m",
                room.x + room.width / 2,
                room.y + room.depth / 2 - 0.28,
                0.12,
            )
            self._dxf_furniture(msp, room)

        for door in unit.doors:
            self._dxf_door(
                msp,
                door.x,
                door.y,
                door.width,
                door.orientation,
            )

        for window in unit.windows:
            self._dxf_window(
                msp,
                window.x,
                window.y,
                window.width,
                window.orientation,
            )

        self._dxf_dimension(
            msp,
            unit.x,
            unit.y,
            unit.x + unit.width,
            unit.y,
            offset=-0.9,
        )
        self._dxf_dimension(
            msp,
            unit.x,
            unit.y,
            unit.x,
            unit.y + unit.depth,
            offset=-0.9,
        )

        

        doc.saveas(path)
