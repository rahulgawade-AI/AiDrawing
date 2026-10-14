from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from townplanning.modules.drawing.inputs import planning_facts_to_inputs
from townplanning.modules.drawing.service import DrawingDesignService


PROJECT_ROOT = Path(__file__).resolve().parents[3]
VISION_PLANNING_SCRIPT = Path(
    os.environ.get(
        "VISION_PLANNING_SCRIPT",
        str(PROJECT_ROOT / "tests/functional/planning/test_vision_to_planning.py"),
    )
)


def _unwrap_values(source: Any) -> dict[str, Any]:
    """Normalize resolved constraint entries without adding values."""
    if not isinstance(source, dict):
        return {}

    result: dict[str, Any] = {}
    for key, raw in source.items():
        if isinstance(raw, dict) and "value" in raw:
            result[key] = raw["value"]
        else:
            result[key] = raw
    return result


def _find_drawing_input(report: Any) -> dict[str, Any]:
    if isinstance(report, dict):
        candidate = report.get("drawing_design_input")
        if isinstance(candidate, dict):
            return candidate

        for child in report.values():
            try:
                return _find_drawing_input(child)
            except LookupError:
                pass

    elif isinstance(report, list):
        for child in report:
            try:
                return _find_drawing_input(child)
            except LookupError:
                pass

    raise LookupError("No drawing_design_input object found in vision-to-planning output")


def _run_vision_to_planning(output_path: Path) -> dict[str, Any]:
    if not VISION_PLANNING_SCRIPT.is_file():
        raise FileNotFoundError(
            f"Vision-to-planning script not found: {VISION_PLANNING_SCRIPT}"
        )

    command = [
        sys.executable,
        str(VISION_PLANNING_SCRIPT),
        "--out",
        str(output_path),
    ]
    user_input_file = os.environ.get("VISION_PLANNING_USER_INPUT")
    if user_input_file:
        command.extend(["--user-input-file", user_input_file])

    image_paths = [
        item.strip()
        for item in os.environ.get("VISION_PLANNING_IMAGES", "").split(os.pathsep)
        if item.strip()
    ]
    for image_path in image_paths:
        command.extend(["--image", image_path])

    answers_file = os.environ.get("VISION_PLANNING_ANSWERS")
    if answers_file:
        command.extend(["--answers", answers_file])

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "The real vision-to-planning pipeline failed "
            f"(exit={completed.returncode}).\n"
            f"Command: {' '.join(command)}\n"
            f"Output:\n{completed.stdout[-12000:]}"
        )
    if not output_path.is_file():
        raise RuntimeError(
            "Vision-to-planning completed but did not create its report at "
            f"{output_path}.\nOutput:\n{completed.stdout[-5000:]}"
        )
    return json.loads(output_path.read_text(encoding="utf-8"))


def _map_drawing_inputs(report: dict[str, Any]):
    drawing_input = _find_drawing_input(report)
    site_data = drawing_input.get("site") or {}
    planning_constraints = drawing_input.get("planning_constraints") or {}
    canonical_facts = planning_constraints.get("canonical_regulatory_facts") or {}
    user_input = report.get("user_input") or {}

    flat_data: dict[str, Any] = {}
    flat_data.update(canonical_facts)
    flat_data.update(user_input)
    flat_data.update(site_data)

    constraints: dict[str, Any] = {}
    constraints.update(_unwrap_values(planning_constraints.get("regulatory_values")))
    constraints.update(
        _unwrap_values(planning_constraints.get("all_final_constraint_values"))
    )
    site, regulatory, preferences, unit_mix = planning_facts_to_inputs(
        flat_data,
        deterministic_constraints=constraints,
    )
    return drawing_input, site, regulatory, preferences, unit_mix


@pytest.fixture(scope="session")
def vision_to_planning_report(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """
    Run the real vision-to-planning test first, then consume its output.
    This deliberately does not use a previously generated JSON file as input.
    """
    output_path = tmp_path_factory.mktemp("vision_to_drawing") / "planning_report.json"
    try:
        return _run_vision_to_planning(output_path)
    except (FileNotFoundError, RuntimeError) as exc:
        pytest.fail(str(exc))


@pytest.fixture(scope="session")
def drawing_inputs(vision_to_planning_report: dict[str, Any]):
    return _map_drawing_inputs(vision_to_planning_report)


def _missing_optimizer_inputs(site, regulatory) -> list[str]:
    missing: list[str] = []

    if site.plot_area_m2 is None:
        missing.append("site.plot_area_m2")
    if regulatory.maximum_height_m is None:
        missing.append("regulatory.maximum_height_m")

    if site.plot_width_m is None:
        missing.append("site.plot_width_m")
    if site.plot_depth_m is None:
        missing.append("site.plot_depth_m")

    for name, value in (
        ("front_setback_m", regulatory.front_setback_m),
        ("rear_setback_m", regulatory.rear_setback_m),
        ("side_setback_left_m", regulatory.side_setback_left_m),
        ("side_setback_right_m", regulatory.side_setback_right_m),
    ):
        if value is None:
            missing.append(f"regulatory.{name}")

    if (
        regulatory.permissible_built_up_area_m2 is None
        and regulatory.permissible_fsi is None
    ):
        missing.append(
            "regulatory.permissible_built_up_area_m2 or regulatory.permissible_fsi"
        )

    return missing


def test_real_vision_to_planning_output_is_mapped_to_drawing_inputs(drawing_inputs):
    drawing_input, site, regulatory, preferences, unit_mix = drawing_inputs

    source_site = drawing_input.get("site") or {}
    if source_site.get("plot_area") is not None:
        assert site.plot_area_m2 == pytest.approx(float(source_site["plot_area"]))

    if source_site.get("plot_width") is not None:
        assert site.plot_width_m == pytest.approx(float(source_site["plot_width"]))

    if source_site.get("plot_depth") is not None:
        assert site.plot_depth_m == pytest.approx(float(source_site["plot_depth"]))

    # Unit mix is checked against upstream user input by the mapper, when supplied.
    # The upstream program's area list alone is not enough to infer unit labels/counts.
    assert isinstance(unit_mix, list)
    assert preferences is not None
    assert regulatory is not None


def test_print_real_vision_to_drawing_inputs(drawing_inputs):
    _, site, regulatory, preferences, unit_mix = drawing_inputs
    drawing_values = {
        "site": asdict(site),
        "regulatory": asdict(regulatory),
        "preferences": asdict(preferences),
        "unit_mix": [asdict(unit) for unit in unit_mix],
    }

    print("\nDRAWING INPUT VALUES")
    print(json.dumps(drawing_values, indent=2, sort_keys=True, default=str))

    assert set(drawing_values) == {"site", "regulatory", "preferences", "unit_mix"}
    assert isinstance(drawing_values["unit_mix"], list)


def test_drawing_generation_uses_real_upstream_inputs_without_fabrication(drawing_inputs):
    _, site, regulatory, preferences, unit_mix = drawing_inputs
    missing = _missing_optimizer_inputs(site, regulatory)

    if missing:
        # This is an expected integration outcome for incomplete upstream facts:
        # the drawing layer must stop rather than invent dimensions/setbacks.
        with pytest.raises(ValueError):
            DrawingDesignService().generate(
                site=site,
                regulatory=regulatory,
                preferences=preferences,
                unit_mix=unit_mix,
            )
        pytest.skip(
            "Vision-to-planning ran, but drawing generation is blocked by missing "
            "source inputs: " + ", ".join(missing)
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


if __name__ == "__main__":
    with TemporaryDirectory(prefix="vision_to_drawing_") as temp_dir:
        report_path = Path(temp_dir) / "planning_report.json"
        report = _run_vision_to_planning(report_path)
    _, site, regulatory, preferences, unit_mix = _map_drawing_inputs(report)
    drawing_values = {
        "site": asdict(site),
        "regulatory": asdict(regulatory),
        "preferences": asdict(preferences),
        "unit_mix": [asdict(unit) for unit in unit_mix],
    }
    print("\nDRAWING INPUT VALUES")
    print(json.dumps(drawing_values, indent=2, sort_keys=True, default=str))
