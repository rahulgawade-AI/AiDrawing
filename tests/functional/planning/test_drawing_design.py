"""Drawing module integration smoke test.

Run from the project root:

    python -m pytest tests/functional/planning/test_drawing_design.py -v
"""

import json

import pytest

from townplanning.modules.drawing.inputs import planning_facts_to_inputs
from townplanning.modules.drawing.service import DrawingDesignService


class FakePlanningFacts:
    """Synthetic planning facts for testing the drawing module adapter."""

    def to_dict(self):
        return {
            "plot_area": 745.6,
            "plot_width": 32.6,
            "plot_depth": 22.3,
            "road_width": 18.0,
            "north_direction": "north",
            "requested_units": 12,
            "requested_unit_mix": [
                {
                    "type": "2BHK",
                    "count": 6,
                    "target_carpet_area": 780.0,
                },
                {
                    "type": "3BHK",
                    "count": 6,
                    "target_carpet_area": 1020.0,
                },
            ],
            "requested_unit_area": {
                "2BHK": 780.0,
                "3BHK": 1020.0,
            },
            "tenement_carpet_area_unit": "sqft",
            "allow_stilt_parking": True,
            "maximize_fsi": True,
            "maximize_usable_area": True,
            "maximize_parking": True,
            "optimize_daylight": True,
            "optimize_ventilation": True,
        }


# TEST FIXTURES ONLY.
# Replace these with actual deterministic resolver output
# when testing the complete planning-to-drawing pipeline.
DETERMINISTIC_CONSTRAINTS = {
    "permissible_fsi": 1.5,
    "maximum_height_m": 30.0,
    "front_setback": 4.5,
    "rear_setback": 3.0,
    "side_setback_left": 3.0,
    "side_setback_right": 3.0,
    "car_parking_required": 9,
    "two_wheeler_parking_required": 12,
    "visitor_parking_required": 0,
    "lift_required": True,
    "lift_count": 1,
    "fire_staircase_required": True,
    "staircase_count": 2,
    "staircase_width_m": 1.5,
    "corridor_width_m": 1.8,
    "minimum_open_space_m2": 100.0,
}


@pytest.fixture
def drawing_inputs():
    """Convert synthetic facts and constraints into drawing inputs."""
    return planning_facts_to_inputs(
        FakePlanningFacts(),
        deterministic_constraints=DETERMINISTIC_CONSTRAINTS,
    )


def test_adapter_preserves_plot_and_unit_mix(drawing_inputs):
    """Verify the adapter carries the supplied values into drawing inputs."""
    site, regulatory, preferences, units = drawing_inputs

    assert site.plot_area_m2 == pytest.approx(745.6)
    assert site.road_width_m == pytest.approx(18.0)

    assert [(unit.name, unit.count) for unit in units] == [
        ("2BHK", 6),
        ("3BHK", 6),
    ]

    # Carpet areas are supplied in square feet and expected in square metres.
    assert units[0].carpet_area_m2 == pytest.approx(780 * 0.092903)
    assert units[1].carpet_area_m2 == pytest.approx(1020 * 0.092903)

    assert regulatory.maximum_height_m == pytest.approx(30.0)
    assert regulatory.front_setback_m == pytest.approx(4.5)
    assert preferences.floor_height_m == pytest.approx(3.0)


def test_missing_height_fails_closed(drawing_inputs):
    """The design service should reject inputs without a maximum height."""
    site, regulatory, preferences, units = drawing_inputs

    regulatory.maximum_height_m = None

    with pytest.raises(ValueError, match="maximum_height_m"):
        DrawingDesignService().generate(
            site=site,
            regulatory=regulatory,
            preferences=preferences,
            unit_mix=units,
        )


def test_missing_geometry_or_setbacks_fails_closed(drawing_inputs):
    """The design service should reject incomplete site geometry."""
    site, regulatory, preferences, units = drawing_inputs

    site.plot_width_m = None

    with pytest.raises(
        ValueError,
        match="geometry|dimensions|setbacks",
    ):
        DrawingDesignService().generate(
            site=site,
            regulatory=regulatory,
            preferences=preferences,
            unit_mix=units,
        )


def test_zero_buildable_area_fails_with_clear_error(drawing_inputs):
    site, regulatory, preferences, units = drawing_inputs
    regulatory.front_setback_m = 20.0
    regulatory.rear_setback_m = 3.0

    with pytest.raises(ValueError, match="no positive buildable site area"):
        DrawingDesignService().generate(
            site=site,
            regulatory=regulatory,
            preferences=preferences,
            unit_mix=units,
        )


def test_maximum_fsi_is_used_as_a_design_cap_when_permissible_fsi_is_absent(
    drawing_inputs,
):
    site, regulatory, preferences, units = drawing_inputs
    regulatory.permissible_fsi = None
    regulatory.maximum_fsi = 1.5

    design, _ = DrawingDesignService().generate(
        site=site,
        regulatory=regulatory,
        preferences=preferences,
        unit_mix=units,
    )

    assert design.total_built_up_area_m2 <= site.plot_area_m2 * regulatory.maximum_fsi


def test_multi_building_output_preserves_each_requested_unit_type(drawing_inputs):
    site, regulatory, preferences, units = drawing_inputs
    preferences.requested_buildings = 2

    design, _ = DrawingDesignService().generate(
        site=site,
        regulatory=regulatory,
        preferences=preferences,
        unit_mix=units,
    )

    aggregate = {}
    for building in design.buildings:
        for unit in building.units:
            aggregate[unit.name] = aggregate.get(unit.name, 0) + unit.count

    assert aggregate == {"2BHK": 6, "3BHK": 6}


def test_square_metre_unit_areas_are_not_converted_as_square_feet():
    facts = FakePlanningFacts().to_dict()
    facts["requested_unit_mix"] = [
        {"type": "2BHK", "count": 1, "target_carpet_area": 70.0}
    ]
    facts["requested_unit_area"] = {"2BHK": 70.0}
    facts["tenement_carpet_area_unit"] = "m2"

    _, _, _, units = planning_facts_to_inputs(facts)

    assert units[0].carpet_area_m2 == pytest.approx(70.0)


def test_service_builds_design_and_cad_payload(
    drawing_inputs,
    tmp_path,
):
    """Smoke-test design generation and the resulting CAD payload."""
    site, regulatory, preferences, units = drawing_inputs

    design, report = DrawingDesignService().generate(
        site=site,
        regulatory=regulatory,
        preferences=preferences,
        unit_mix=units,
    )

    assert design.buildings
    assert design.total_built_up_area_m2 > 0
    assert design.fsi_used > 0

    assert report["validation"]["status"] in {"PASS", "FAIL"}

    payload = report["cad_payload"]

    assert payload["units"] == "m"
    assert payload["buildings"]
    assert payload["parking"]["car_spaces"] == 9
    assert payload["parking"]["two_wheeler_spaces"] == 12

    output_file = tmp_path / "drawing_test_output.json"
    output_file.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )

    assert output_file.exists()
