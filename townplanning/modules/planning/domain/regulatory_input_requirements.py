"""Application facts required before regulatory evidence can be resolved."""

from __future__ import annotations

from typing import Any


FIELD_INPUT_REQUIREMENTS = {
    "front_setback": {"required": ("road_width",)},
    "rear_setback": {"required": ("road_width",)},
    "side_setback_left": {"required": ("road_width",)},
    "side_setback_right": {"required": ("road_width",)},
    "basic_fsi": {"required": ("road_width",)},
    "premium_fsi": {"required": ("road_width",)},
    "tdr_fsi": {"required": ("road_width",)},
    "maximum_fsi": {"required": ("road_width",)},
    "car_parking_required": {
        "required": ("occupancy", "tenement_carpet_areas")
    },
    "two_wheeler_parking_required": {
        "required": ("occupancy", "tenement_carpet_areas")
    },
    "visitor_parking_required": {
        "required": ("occupancy", "tenement_carpet_areas")
    },
    "parking_factor": {"required": ("planning_authority",)},
}


def validate_required_inputs(
    facts: Any,
    requested_fields: list[str],
) -> tuple[dict[str, list[str]], list[str]]:
    """Return blocked constraints and unique missing fact names."""
    facts_values = getattr(facts, "values", {})
    blocked: dict[str, list[str]] = {}
    missing_inputs: list[str] = []

    for field in requested_fields:
        requirement = FIELD_INPUT_REQUIREMENTS.get(field)
        if not requirement:
            continue

        missing: list[str] = []
        for input_name in requirement["required"]:
            value = getattr(facts, input_name, None)
            if value is None and isinstance(facts_values, dict):
                value = facts_values.get(input_name)

            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(input_name)
                continue

            if input_name == "tenement_carpet_areas":
                if not isinstance(value, (list, tuple)):
                    value = [value]
                if not value:
                    missing.append(input_name)

        if missing:
            blocked[field] = missing
            for input_name in missing:
                if input_name not in missing_inputs:
                    missing_inputs.append(input_name)

    return blocked, missing_inputs
