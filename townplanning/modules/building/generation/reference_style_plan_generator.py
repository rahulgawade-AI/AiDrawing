"""
reference_style_plan_generator.py

Generate AutoCAD-compatible DXF floor plans in the style of the
user-supplied residential reference drawing.

IMPORTANT:
- This creates REAL CAD geometry: walls, partitions, doors, windows,
  room labels, dimensions, furniture and sanitary fixtures.
- The same geometry can be rendered separately.
- No AI call is required for this module. It is deterministic.
- Use metres internally.
- DXF can be opened in AutoCAD and saved as DWG.

Install:
    pip install ezdxf

Example:
    from reference_style_plan_generator import generate_plan

    generate_plan(
        output="B01_floor_01_reference.dxf",
        units=[
            {
                "id": "U01",
                "type": "2BHK",
                "area_sqft": 692.73,
                "x": 0,
                "y": 0,
                "width": 10.90,
                "depth": 12.00,
            },
            {
                "id": "U02",
                "type": "1BHK",
                "area_sqft": 408.07,
                "x": 10.90,
                "y": 0,
                "width": 9.90,
                "depth": 11.00,
            },
        ],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
import math

import ezdxf
from ezdxf import units


# ================================================================
# DATA MODEL
# ================================================================

@dataclass
class UnitSpec:
    unit_id: str
    unit_type: str
    x: float
    y: float
    width: float
    depth: float
    area_sqft: float | None = None


@dataclass
class Room:
    name: str
    room_type: str
    x: float
    y: float
    width: float
    depth: float
    metadata: dict = field(default_factory=dict)


# ================================================================
# CAD LAYERS
# ================================================================

LAYERS = {
    "A-WALL": 7,
    "A-PARTITION": 8,
    "A-ROOM": 30,
    "A-BALCONY": 33,
    "A-DOOR": 1,
    "A-WINDOW": 4,
    "A-FURN": 140,
    "A-SANITARY": 150,
    "A-KITCHEN": 32,
    "A-TEXT": 7,
    "A-DIMS": 6,
    "A-AREA": 3,
}


# ================================================================
# BASIC CAD HELPERS
# ================================================================

def _rect(msp, x, y, w, h, layer="A-PARTITION", closed=True):
    points = [
        (x, y),
        (x + w, y),
        (x + w, y + h),
        (x, y + h),
    ]
    if closed:
        points.append(points[0])

    return msp.add_lwpolyline(
        points,
        dxfattribs={"layer": layer}
    )


def _line(msp, x1, y1, x2, y2, layer="A-PARTITION"):
    return msp.add_line(
        (x1, y1),
        (x2, y2),
        dxfattribs={"layer": layer}
    )


def _text(
    msp,
    x,
    y,
    value,
    height=0.16,
    layer="A-TEXT",
    rotation=0,
):
    entity = msp.add_text(
        str(value),
        dxfattribs={
            "height": height,
            "layer": layer,
            "rotation": rotation,
        },
    )
    entity.set_placement((x, y))
    return entity


def _center_text(msp, x, y, value, height=0.16, layer="A-TEXT"):
    return _text(
        msp,
        x,
        y,
        value,
        height=height,
        layer=layer,
    )


def _wall_box(msp, x, y, w, h, thickness=0.20):
    """
    Draw a thick wall as an outer and inner closed rectangle.

    The reference drawing has visually heavy external walls.
    """
    _rect(msp, x, y, w, h, "A-WALL")

    # Inner rectangle gives a proper wall-band appearance.
    if w > 2 * thickness and h > 2 * thickness:
        _rect(
            msp,
            x + thickness,
            y + thickness,
            w - 2 * thickness,
            h - 2 * thickness,
            "A-WALL",
        )


def _door(msp, hinge_x, hinge_y, width=0.90, swing="up"):
    """
    Door leaf + swing arc.

    Coordinates are metres.
    """
    _line(
        msp,
        hinge_x,
        hinge_y,
        hinge_x + width,
        hinge_y,
        "A-DOOR",
    )

    if swing == "up":
        center = (hinge_x, hinge_y)
        start_angle = 0
        end_angle = 90
    elif swing == "left":
        center = (hinge_x, hinge_y)
        start_angle = 90
        end_angle = 180
    elif swing == "down":
        center = (hinge_x, hinge_y)
        start_angle = 180
        end_angle = 270
    else:
        center = (hinge_x, hinge_y)
        start_angle = 270
        end_angle = 360

    msp.add_arc(
        center,
        width,
        start_angle,
        end_angle,
        dxfattribs={"layer": "A-DOOR"},
    )


def _window(msp, x1, y1, x2, y2):
    """
    Window shown as a pair of thin CAD lines.
    """
    _line(msp, x1, y1, x2, y2, "A-WINDOW")

    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)

    if length == 0:
        return

    nx = -dy / length * 0.035
    ny = dx / length * 0.035

    _line(
        msp,
        x1 + nx,
        y1 + ny,
        x2 + nx,
        y2 + ny,
        "A-WINDOW",
    )


def _dimension_horizontal(msp, x1, x2, y, text):
    _line(msp, x1, y, x2, y, "A-DIMS")
    _line(msp, x1, y - 0.08, x1, y + 0.08, "A-DIMS")
    _line(msp, x2, y - 0.08, x2, y + 0.08, "A-DIMS")

    _center_text(
        msp,
        (x1 + x2) / 2,
        y + 0.12,
        text,
        height=0.12,
        layer="A-DIMS",
    )


def _dimension_vertical(msp, x, y1, y2, text):
    _line(msp, x, y1, x, y2, "A-DIMS")
    _line(msp, x - 0.08, y1, x + 0.08, y1, "A-DIMS")
    _line(msp, x - 0.08, y2, x + 0.08, y2, "A-DIMS")

    _text(
        msp,
        x + 0.12,
        (y1 + y2) / 2,
        text,
        height=0.12,
        layer="A-DIMS",
        rotation=90,
    )


# ================================================================
# FURNITURE
# ================================================================

def _bed(msp, x, y, w=1.80, h=2.00):
    _rect(msp, x, y, w, h, "A-FURN")

    # pillows
    _rect(msp, x + 0.10, y + h - 0.40, w * 0.36, 0.25, "A-FURN")
    _rect(msp, x + w * 0.54, y + h - 0.40, w * 0.36, 0.25, "A-FURN")

    # center split
    _line(
        msp,
        x + w / 2,
        y + h - 0.15,
        x + w / 2,
        y + h - 0.55,
        "A-FURN",
    )


def _wardrobe(msp, x, y, w, h):
    _rect(msp, x, y, w, h, "A-FURN")
    _line(msp, x + w / 2, y, x + w / 2, y + h, "A-FURN")


def _sofa(msp, x, y, w, h=0.80):
    _rect(msp, x, y, w, h, "A-FURN")
    _line(msp, x, y + h * 0.72, x + w, y + h * 0.72, "A-FURN")


def _coffee_table(msp, x, y, w=0.90, h=0.50):
    _rect(msp, x, y, w, h, "A-FURN")


def _dining_table(msp, x, y, w=1.20, h=0.75):
    _rect(msp, x, y, w, h, "A-FURN")

    # chairs
    chair = 0.32
    for cx, cy in [
        (x - chair, y + h / 2 - chair / 2),
        (x + w, y + h / 2 - chair / 2),
        (x + w / 2 - chair / 2, y - chair),
        (x + w / 2 - chair / 2, y + h),
    ]:
        _rect(msp, cx, cy, chair, chair, "A-FURN")


def _kitchen_counter(msp, x, y, w, h):
    _rect(msp, x, y, w, h, "A-KITCHEN")

    # counter divisions
    if w > 1.5:
        for i in range(1, 3):
            xx = x + w * i / 3
            _line(msp, xx, y, xx, y + h, "A-KITCHEN")

    # sink
    _rect(
        msp,
        x + w * 0.55,
        y + h * 0.25,
        min(0.55, w * 0.25),
        min(0.40, h * 0.35),
        "A-SANITARY",
    )


def _toilet_fixture(msp, x, y, w, h):
    """
    Simple CAD sanitary layout:
      shower, WC and wash basin.
    """
    _rect(msp, x, y, w, h, "A-SANITARY")

    # Shower circle
    r = min(w, h) * 0.12
    msp.add_circle(
        (x + w * 0.23, y + h * 0.70),
        r,
        dxfattribs={"layer": "A-SANITARY"},
    )

    # WC
    msp.add_circle(
        (x + w * 0.50, y + h * 0.28),
        min(w, h) * 0.10,
        dxfattribs={"layer": "A-SANITARY"},
    )

    # Basin
    msp.add_circle(
        (x + w * 0.78, y + h * 0.70),
        min(w, h) * 0.08,
        dxfattribs={"layer": "A-SANITARY"},
    )


def _balcony_furniture(msp, x, y, w, h):
    """
    Two chairs + round table.
    """
    r = min(w, h) * 0.12

    for cx, cy in [
        (x + w * 0.68, y + h * 0.55),
        (x + w * 0.82, y + h * 0.55),
    ]:
        msp.add_circle(
            (cx, cy),
            r,
            dxfattribs={"layer": "A-FURN"},
        )

    msp.add_circle(
        (x + w * 0.75, y + h * 0.55),
        r * 0.70,
        dxfattribs={"layer": "A-FURN"},
    )


# ================================================================
# ROOM TEMPLATES
# ================================================================

def layout_1bhk(u: UnitSpec) -> list[Room]:
    """
    Reference-like 1BHK:
      - Living room toward balcony
      - Bedroom at rear
      - Kitchen beside living
      - Bath/WC grouped near kitchen/bedroom
      - Dry balcony beside kitchen
    """
    x, y, w, d = u.x, u.y, u.width, u.depth

    balcony_h = 1.20
    kitchen_w = min(2.40, w * 0.34)
    kitchen_h = min(2.40, d * 0.25)

    living_h = min(3.96, d * 0.38)
    bedroom_w = min(3.35, w * 0.45)
    bedroom_h = min(3.40, d * 0.34)

    bath_w = 1.72
    bath_h = 1.22
    wc_w = 0.90
    wc_h = 1.25

    rooms = [
        Room(
            "BALCONY",
            "balcony",
            x,
            y + d - balcony_h,
            w,
            balcony_h,
        ),
        Room(
            "LIVING ROOM",
            "living",
            x,
            y + d - balcony_h - living_h,
            w - kitchen_w * 0.10,
            living_h,
        ),
        Room(
            "BED ROOM",
            "bedroom",
            x + w - bedroom_w,
            y + d - balcony_h - bedroom_h,
            bedroom_w,
            bedroom_h,
        ),
        Room(
            "KITCHEN",
            "kitchen",
            x,
            y,
            kitchen_w,
            kitchen_h,
        ),
        Room(
            "BATH",
            "bath",
            x + w - bath_w,
            y + kitchen_h,
            bath_w,
            bath_h,
        ),
        Room(
            "WC",
            "wc",
            x + w - wc_w,
            y + kitchen_h - wc_h,
            wc_w,
            wc_h,
        ),
        Room(
            "DRY BALCONY",
            "dry_balcony",
            x + kitchen_w,
            y,
            max(1.20, w - kitchen_w - 0.10),
            min(1.25, kitchen_h),
        ),
    ]

    return rooms


def layout_2bhk(u: UnitSpec) -> list[Room]:
    """
    Reference-like 2BHK:
      - Large living room at balcony side
      - Two bedrooms on external walls
      - Two toilets grouped centrally
      - Kitchen at lower side
      - Dry balcony beside kitchen
    """
    x, y, w, d = u.x, u.y, u.width, u.depth

    balcony_h = 1.30
    kitchen_w = min(3.06, w * 0.32)
    kitchen_h = min(2.33, d * 0.22)

    living_h = min(3.98, d * 0.34)

    bed1_w = min(3.06, w * 0.31)
    bed1_h = min(3.26, d * 0.30)

    bed2_w = min(3.04, w * 0.31)
    bed2_h = min(3.25, d * 0.30)

    toilet1_w, toilet1_h = 2.50, 1.20
    toilet2_w, toilet2_h = 2.19, 1.22

    rooms = [
        Room(
            "BALCONY",
            "balcony",
            x,
            y + d - balcony_h,
            w * 0.48,
            balcony_h,
        ),
        Room(
            "BALCONY",
            "balcony",
            x + w * 0.68,
            y + d - 0.90,
            w * 0.32,
            0.90,
        ),
        Room(
            "LIVING ROOM",
            "living",
            x,
            y + d - balcony_h - living_h,
            w * 0.62,
            living_h,
        ),
        Room(
            "BEDROOM",
            "bedroom",
            x + w * 0.36,
            y + d - balcony_h - bed1_h,
            bed1_w,
            bed1_h,
        ),
        Room(
            "BEDROOM",
            "bedroom",
            x + w * 0.69,
            y + d - 0.90 - bed2_h,
            bed2_w,
            bed2_h,
        ),
        Room(
            "TOILET",
            "toilet",
            x + w * 0.52,
            y + d * 0.32,
            toilet1_w,
            toilet1_h,
        ),
        Room(
            "TOILET",
            "toilet",
            x + w * 0.72,
            y + d * 0.32,
            toilet2_w,
            toilet2_h,
        ),
        Room(
            "KITCHEN",
            "kitchen",
            x + 0.80,
            y,
            kitchen_w,
            kitchen_h,
        ),
        Room(
            "DRY BALCONY",
            "dry_balcony",
            x + kitchen_w + 0.80,
            y,
            max(1.20, w - kitchen_w - 1.00),
            min(1.20, kitchen_h),
        ),
    ]

    return rooms


def generate_rooms(u: UnitSpec) -> list[Room]:
    t = u.unit_type.upper().replace(" ", "")

    if t in {"1BHK", "1-BHK"}:
        return layout_1bhk(u)

    if t in {"2BHK", "2-BHK"}:
        return layout_2bhk(u)

    raise ValueError(
        f"Unsupported unit type {u.unit_type!r}. "
        "Add another deterministic template instead of "
        "letting an LLM invent CAD coordinates."
    )


# ================================================================
# ROOM DRAWING
# ================================================================

def draw_room(msp, room: Room):
    x, y, w, h = room.x, room.y, room.width, room.depth

    if room.room_type == "balcony":
        _rect(msp, x, y, w, h, "A-BALCONY")
        _balcony_furniture(msp, x, y, w, h)

    elif room.room_type == "dry_balcony":
        _rect(msp, x, y, w, h, "A-BALCONY")

    elif room.room_type in {"bath", "wc", "toilet"}:
        _rect(msp, x, y, w, h, "A-PARTITION")
        _toilet_fixture(msp, x, y, w, h)

    elif room.room_type == "kitchen":
        _rect(msp, x, y, w, h, "A-PARTITION")
        _kitchen_counter(msp, x + 0.10, y + 0.10, max(0.8, w - 0.20), max(0.7, h - 0.20))

    else:
        _rect(msp, x, y, w, h, "A-PARTITION")

    # Room label
    label = room.name
    area = room.width * room.depth

    _center_text(
        msp,
        x + w / 2,
        y + h / 2 + 0.12,
        label,
        height=0.15,
    )

    _center_text(
        msp,
        x + w / 2,
        y + h / 2 - 0.12,
        f"{w:.2f} X {h:.2f} m",
        height=0.11,
    )

    _center_text(
        msp,
        x + w / 2,
        y + h / 2 - 0.30,
        f"{area:.1f} m²",
        height=0.10,
    )

    # Furniture according to room function
    if room.room_type == "bedroom":
        _bed(
            msp,
            x + 0.30,
            y + max(0.25, h * 0.20),
            min(1.80, w * 0.55),
            min(2.00, h * 0.55),
        )
        _wardrobe(
            msp,
            x + max(0.20, w - 0.45),
            y + 0.25,
            0.35,
            max(0.80, h - 0.50),
        )

    elif room.room_type == "living":
        _sofa(
            msp,
            x + 0.30,
            y + h * 0.48,
            min(2.40, w * 0.45),
        )
        _coffee_table(
            msp,
            x + w * 0.42,
            y + h * 0.25,
        )
        _dining_table(
            msp,
            x + w * 0.65,
            y + h * 0.48,
            min(1.20, w * 0.20),
            0.70,
        )

    elif room.room_type == "kitchen":
        # appliance symbols
        _rect(
            msp,
            x + 0.20,
            y + h - 0.65,
            0.45,
            0.45,
            "A-KITCHEN",
        )

    # Opening markers
    if room.room_type == "balcony":
        _window(
            msp,
            x + w * 0.25,
            y,
            x + w * 0.75,
            y,
        )


# ================================================================
# UNIT DRAWING
# ================================================================

def draw_unit(msp, unit: UnitSpec):
    # External wall
    _wall_box(
        msp,
        unit.x,
        unit.y,
        unit.width,
        unit.depth,
        thickness=0.20,
    )

    rooms = generate_rooms(unit)

    for room in rooms:
        draw_room(msp, room)

    # Main entrance
    _door(
        msp,
        unit.x + unit.width * 0.18,
        unit.y,
        width=0.90,
        swing="up",
    )

    # Internal door markers
    for room in rooms:
        if room.room_type in {
            "bedroom",
            "bath",
            "wc",
            "toilet",
            "kitchen",
        }:
            _door(
                msp,
                room.x + room.width * 0.45,
                room.y,
                width=min(0.80, room.width * 0.30),
                swing="up",
            )

    # External windows on balcony-facing and bedroom-facing walls
    for room in rooms:
        if room.room_type in {"balcony", "bedroom", "living"}:
            _window(
                msp,
                room.x + room.width * 0.25,
                room.y + room.depth,
                room.x + room.width * 0.65,
                room.y + room.depth,
            )

    # Unit label
    _center_text(
        msp,
        unit.x + unit.width / 2,
        unit.y + unit.depth + 0.55,
        f"{unit.unit_id}  {unit.unit_type}",
        height=0.20,
    )

    if unit.area_sqft:
        _center_text(
            msp,
            unit.x + unit.width / 2,
            unit.y + unit.depth + 0.25,
            f"CARPET AREA — {unit.area_sqft:.2f} SQ.FT.",
            height=0.12,
            layer="A-AREA",
        )

    # Overall dimensions
    _dimension_horizontal(
        msp,
        unit.x,
        unit.x + unit.width,
        unit.y - 0.55,
        f"{unit.width:.2f} m",
    )

    _dimension_vertical(
        msp,
        unit.x - 0.55,
        unit.y,
        unit.y + unit.depth,
        f"{unit.depth:.2f} m",
    )


# ================================================================
# PUBLIC API
# ================================================================

def generate_plan(
    output: str | Path,
    units: Iterable[dict | UnitSpec],
    title: str = "RESIDENTIAL FLOOR PLAN",
) -> Path:

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new("R2018")
    doc.units = units.M if hasattr(units, "M") else 6

    # Create layers
    for name, color in LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, color=color)

    msp = doc.modelspace()

    # Sheet border
    unit_list: list[UnitSpec] = []

    for u in units:
        if isinstance(u, UnitSpec):
            unit_list.append(u)
        else:
            unit_list.append(UnitSpec(**u))

    if not unit_list:
        raise ValueError("At least one unit is required.")

    min_x = min(u.x for u in unit_list)
    min_y = min(u.y for u in unit_list)
    max_x = max(u.x + u.width for u in unit_list)
    max_y = max(u.y + u.depth for u in unit_list)

    margin = 2.0

    _rect(
        msp,
        min_x - margin,
        min_y - margin,
        max_x - min_x + 2 * margin,
        max_y - min_y + 2 * margin,
        "A-WALL",
    )

    _text(
        msp,
        min_x - margin + 0.3,
        max_y + margin - 0.45,
        title,
        height=0.30,
    )

    for u in unit_list:
        draw_unit(msp, u)

    # North arrow
    nx = max_x + margin - 0.5
    ny = max_y + margin - 0.5

    _line(msp, nx, ny - 1.4, nx, ny, "A-TEXT")
    _line(msp, nx, ny, nx - 0.12, ny - 0.25, "A-TEXT")
    _line(msp, nx, ny, nx + 0.12, ny - 0.25, "A-TEXT")
    _text(msp, nx, ny + 0.20, "N", 0.22)

    # Footer note
    _text(
        msp,
        min_x - margin + 0.3,
        min_y - margin + 0.30,
        "CONCEPTUAL PLAN - VERIFY WITH ARCHITECTURAL / STATUTORY DRAWINGS",
        0.11,
        "A-TEXT",
    )

    doc.saveas(output)
    return output


# ================================================================
# SAMPLE COMMAND-LINE USAGE
# ================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate reference-style residential DXF."
    )
    parser.add_argument(
        "--output",
        default="reference_style_floor_plan.dxf",
    )

    args = parser.parse_args()

    generate_plan(
        args.output,
        [
            {
                "unit_id": "U01",
                "unit_type": "2BHK",
                "x": 0.0,
                "y": 0.0,
                "width": 10.90,
                "depth": 12.00,
                "area_sqft": 692.73,
            },
            {
                "unit_id": "U02",
                "unit_type": "1BHK",
                "x": 12.50,
                "y": 0.0,
                "width": 9.90,
                "depth": 11.00,
                "area_sqft": 408.07,
            },
        ],
    )
