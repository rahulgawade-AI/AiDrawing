from __future__ import annotations
from typing import Any
from .models import DesignPreferences, RegulatoryInputs, SiteGeometry, UnitType

def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None

def _int(v: Any) -> int | None:
    try:
        return None if v is None else int(v)
    except (TypeError, ValueError):
        return None

def _value(constraints: dict[str, Any], name: str) -> Any:
    v = constraints.get(name)
    return v.get("value") if isinstance(v, dict) and "value" in v else v


def _area_to_m2(value: Any, unit: Any) -> float | None:
    area = _num(value)
    if area is None:
        return None

    normalized_unit = str(unit or "sqft").strip().lower().replace(" ", "_")
    factors = {
        "m2": 1.0,
        "sqm": 1.0,
        "sq.m": 1.0,
        "sq.m.": 1.0,
        "square_meter": 1.0,
        "square_metre": 1.0,
        "sqft": 0.09290304,
        "sq.ft": 0.09290304,
        "sq.ft.": 0.09290304,
        "square_feet": 0.09290304,
        "square_foot": 0.09290304,
    }
    try:
        factor = factors[normalized_unit]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported tenement_carpet_area_unit: {unit!r}"
        ) from exc
    return area * factor

def planning_facts_to_inputs(
    facts: Any,
    deterministic_constraints: dict[str, Any] | None = None,
):
    data = facts.to_dict() if hasattr(facts, "to_dict") else dict(facts or {})
    constraints = deterministic_constraints or data.get("regulatory_values", {}) or {}
    def get(name: str):
        v = _value(constraints, name)
        return data.get(name) if v is None else v

    site = SiteGeometry(
        plot_area_m2=_num(data.get("plot_area")),
        boundary=data.get("boundary") or data.get("boundary_geometry"),
        plot_width_m=_num(data.get("plot_width")),
        plot_depth_m=_num(data.get("plot_depth")),
        north_direction=data.get("north_direction"),
        road_width_m=_num(data.get("road_width")),
    )
    regulatory = RegulatoryInputs(
        plot_area_m2=site.plot_area_m2,
        plot_width_m=site.plot_width_m,
        plot_depth_m=site.plot_depth_m,
        road_width_m=site.road_width_m,
        permissible_fsi=_num(get("permissible_fsi")),
        maximum_fsi=_num(get("maximum_fsi")),
        permissible_built_up_area_m2=_num(get("permissible_built_up_area")),
        maximum_built_up_area_m2=_num(get("maximum_built_up_area")),
        maximum_height_m=_num(get("maximum_height_m")),
        front_setback_m=_num(get("front_setback")),
        rear_setback_m=_num(get("rear_setback")),
        side_setback_left_m=_num(get("side_setback_left")),
        side_setback_right_m=_num(get("side_setback_right")),
        minimum_open_space_m2=_num(get("minimum_open_space_m2")),
        recreational_open_space_m2=_num(get("recreational_open_space_m2")),
        amenity_space_m2=_num(get("amenity_space_m2")),
        car_parking_required=_int(get("car_parking_required")),
        two_wheeler_parking_required=_int(get("two_wheeler_parking_required")),
        visitor_parking_required=get("visitor_parking_required"),
        fire_access_required=get("fire_access_required"),
        fire_lift_required=get("fire_lift_required"),
        fire_lift_count=_int(get("fire_lift_count")),
        fire_staircase_required=get("fire_staircase_required"),
        staircase_count=_int(get("staircase_count")),
        staircase_width_m=_num(get("staircase_width_m")),
        corridor_width_m=_num(get("corridor_width_m")),
        lift_required=get("lift_required"),
        lift_count=_int(get("lift_count")),
        accessible_entrance_required=get("accessible_entrance_required"),
        refuge_area_required=get("refuge_area_required"),
        building_separation_m=_num(get("building_separation")),
    )
    prefs = DesignPreferences(
        floor_height_m=_num(data.get("floor_height")) or 3.0,
        requested_units=_int(data.get("requested_units")),
        requested_buildings=_int(data.get("number_of_buildings")),
        allow_basement=data.get("avoid_basement") is not True,
        allow_stilt=bool(data.get("allow_stilt_parking", True)),
        maximize_fsi=bool(data.get("maximize_fsi", True)),
        maximize_usable_area=bool(data.get("maximize_usable_area", True)),
        maximize_parking=bool(data.get("maximize_parking", True)),
        optimize_daylight=bool(data.get("optimize_daylight", True)),
        optimize_ventilation=bool(data.get("optimize_ventilation", True)),
        preferred_orientation=data.get("preferred_orientation"),
    )
    units = []
    mix = data.get("requested_unit_mix") or []
    areas = data.get("requested_unit_area") or {}
    area_unit = data.get("tenement_carpet_area_unit", "sqft")
    for item in mix:
        if not isinstance(item, dict):
            continue
        name = str(item.get("type") or "").strip()
        count = _int(item.get("count"))
        raw_area = _num(areas.get(name)) if isinstance(areas, dict) else None
        if raw_area is None:
            raw_area = _num(item.get("target_carpet_area"))
        area_m2 = _area_to_m2(raw_area, area_unit)
        if name and count and count > 0 and area_m2 and area_m2 > 0:
            units.append(UnitType(name, count, area_m2))
    return site, regulatory, prefs, units
