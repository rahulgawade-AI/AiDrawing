from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from townplanning.modules.drawing.inputs import planning_facts_to_inputs
from townplanning.modules.drawing.service import DrawingDesignService


REPORT_PATH = Path(
    os.environ.get(
        "VISION_PLANNING_REPORT",
        "/tmp/vision_to_planning_design_input.json",
    )
)


def _find_drawing_input(value: Any) -> dict[str, Any] | None:
    """Find drawing_design_input in either a single report or a nested/multi-case report."""
    if isinstance(value, dict):
        candidate = value.get("drawing_design_input")
        if isinstance(candidate, dict):
            return candidate

        # Also accept a file containing drawing_design_input directly.
        if {"site", "planning_constraints", "program"}.issubset(value):
            return value

        for child in value.values():
            found = _find_drawing_input(child)
            if found is not None:
                return found

    elif isinstance(value, list):
        for child in value:
            found = _find_drawing_input(child)
            if found is not None:
                return found

    return None


def _find_named_dict(value: Any, name: str) -> dict[str, Any]:
    if isinstance(value, dict):
        candidate = value.get(name)
        if isinstance(candidate, dict):
            return candidate
        for child in value.values():
            found = _find_named_dict(child, name)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_named_dict(child, name)
            if found:
                return found
    return {}


def _unwrap_constraint_values(
    planning_constraints: dict[str, Any],
) -> dict[str, Any]:
    """Prefer final resolved constraints; preserve only values present in the report."""
    values: dict[str, Any] = {}

    # Seed from regulatory_values, then let all_final_constraint_values take priority.
    sources = (
        planning_constraints.get("regulatory_values") or {},
        planning_constraints.get("all_final_constraint_values") or {},
    )

    for source in sources:
        if not isinstance(source, dict):
            continue
        for name, raw in source.items():
            if isinstance(raw, dict) and "value" in raw:
                values[name] = raw["value"]
            else:
                values[name] = raw

    return values


def _load_and_map_report():
    if not REPORT_PATH.is_file():
        pytest.fail(
            f"Planning report not found: {REPORT_PATH}. "
            "Run test_vision_to_planning.py first, or set "
            "VISION_PLANNING_REPORT=/path/to/report.json."
        )

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    drawing_input = _find_drawing_input(report)
    if drawing_input is None:
        pytest.fail(
            "No drawing_design_input object was found in the planning report. "
            f"Top-level keys: {list(report) if isinstance(report, dict) else type(report).__name__}"
        )

    site_data = drawing_input.get("site") or {}
    planning_constraints = drawing_input.get("planning_constraints") or {}
    design_constraints = drawing_input.get("design_constraints") or {}
    program_data = design_constraints.get("program") or {}
    user_input = _find_named_dict(report, "user_input")

    # Explicit project/program facts are taken from the report. Site facts from
    # drawing_design_input.site override same-named user-input values.
    flat_data: dict[str, Any] = {}
    flat_data.update(user_input)
    flat_data.update(program_data)
    flat_data.update(site_data)

    constraints = _unwrap_constraint_values(planning_constraints)
    site, regulatory, preferences, unit_mix = planning_facts_to_inputs(
        flat_data,
        deterministic_constraints=constraints,
    )

    return report, drawing_input, site, regulatory, preferences, unit_mix


def _geometry_inputs_missing(site, regulatory) -> list[str]:
    missing: list[str] = []

    if site.plot_width_m is None:
        missing.append("plot_width")
    if site.plot_depth_m is None:
        missing.append("plot_depth")

    for field_name, value in (
        ("front_setback", regulatory.front_setback_m),
        ("rear_setback", regulatory.rear_setback_m),
        ("side_setback_left", regulatory.side_setback_left_m),
        ("side_setback_right", regulatory.side_setback_right_m),
    ):
        if value is None:
            missing.append(field_name)

    return missing


def test_real_planning_report_maps_to_drawing_models():
    """Check mapping from the real vision-to-planning JSON; no regulatory fixtures."""
    _, drawing_input, site, regulatory, _, unit_mix = _load_and_map_report()

    site_data = drawing_input.get("site") or {}
    assert site.plot_area_m2 == pytest.approx(float(site_data["plot_area"]))
    assert site.road_width_m == pytest.approx(float(site_data["road_width"]))

    # This uploaded report describes 12 requested tenements: six 2BHK and six 3BHK.
    assert sum(unit.count for unit in unit_mix) == 12
    assert {unit.name: unit.count for unit in unit_mix} == {
        "2BHK": 6,
        "3BHK": 6,
    }

    # These checks only verify that source values were mapped; they do not certify
    # that the source values are legally correct or that the proposal is compliant.
    assert regulatory.maximum_height_m is not None
    assert (
        regulatory.permissible_fsi is not None
        or regulatory.maximum_fsi is not None
        or regulatory.permissible_built_up_area_m2 is not None
    )


def test_optimizer_refuses_to_invent_missing_geometry():
    """With the current report, missing dimensions/setbacks must stop generation."""
    _, _, site, regulatory, preferences, unit_mix = _load_and_map_report()
    missing = _geometry_inputs_missing(site, regulatory)

    if not missing:
        pytest.skip(
            "The report now contains rectangular dimensions and all four setbacks; "
            "the successful-generation test covers that case."
        )

    # The optimizer currently supports rectangular dimensions plus four setbacks.
    # A descriptive boundary string and side-length labels are not a metric polygon.
    with pytest.raises(
        ValueError,
        match="Actual plot geometry or rectangular dimensions plus all applicable setbacks",
    ):
        DrawingDesignService().generate(
            site=site,
            regulatory=regulatory,
            preferences=preferences,
            unit_mix=unit_mix,
        )


def test_successful_drawing_generation_when_geometry_inputs_are_available():
    """Exercise design, validation and CAD payload when source geometry is sufficient."""
    _, _, site, regulatory, preferences, unit_mix = _load_and_map_report()
    missing = _geometry_inputs_missing(site, regulatory)

    if missing:
        pytest.skip(
            "Cannot generate a drawing from this report yet. Missing source inputs: "
            + ", ".join(missing)
        )

    design, output = DrawingDesignService().generate(
        site=site,
        regulatory=regulatory,
        preferences=preferences,
        unit_mix=unit_mix,
    )

    assert design.buildings
    assert isinstance(output, dict)
    assert "design" in output
    assert "validation" in output
    assert "cad_payload" in output
    assert output["design"]["buildings"]
