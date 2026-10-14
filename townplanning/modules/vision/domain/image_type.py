from __future__ import annotations

from enum import Enum


class ImageType(str, Enum):
    UNKNOWN = "unknown"

    SITE_PLAN = "site_plan"
    HAND_DRAWN_SITE_PLAN = "hand_drawn_site_plan"

    SURVEY_PLAN = "survey_plan"
    LAYOUT_PLAN = "layout_plan"

    FLOOR_PLAN = "floor_plan"
    BUILDING_PLAN = "building_plan"

    CAD_DRAWING = "cad_drawing"

    SATELLITE_IMAGE = "satellite_image"
    AERIAL_IMAGE = "aerial_image"

    PHOTOGRAPH = "photograph"
    DOCUMENT_SCAN = "document_scan"

    MAP = "map"

    MIXED = "mixed"