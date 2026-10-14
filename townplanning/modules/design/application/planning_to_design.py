from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from townplanning.modules.design.domain.design_constraints import (
    AccessConstraints,
    BuildingProgram,
    DesignConstraints,
    DesignObjectives,
    FSIConstraints,
    HeightConstraints,
    ParkingConstraints,
    SetbackConstraints,
    SiteConstraints,
)


# ---------------------------------------------------------------------------
# Generic serialization helpers
# ---------------------------------------------------------------------------

def _plain(value: Any) -> Any:
    """
    Convert PlanningFacts / resolver objects into plain Python structures.
    """

    if value is None:
        return None

    for method_name in (
        "to_dict",
        "model_dump",
        "dict",
    ):
        method = getattr(value, method_name, None)

        if callable(method):
            try:
                return method()
            except Exception:
                pass

    if isinstance(value, dict):
        return {
            str(k): _plain(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _plain(v)
            for v in value
        ]

    if hasattr(value, "__dict__"):
        return {
            str(k): _plain(v)
            for k, v in vars(value).items()
            if not str(k).startswith("_")
        }

    return value


def _flatten(
    value: Any,
    prefix: str = "",
) -> Dict[str, Any]:

    result: Dict[str, Any] = {}

    if isinstance(value, dict):

        for key, item in value.items():

            child = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            result.update(
                _flatten(item, child)
            )

    elif isinstance(value, (list, tuple)):

        for index, item in enumerate(value):

            child = (
                f"{prefix}[{index}]"
            )

            result.update(
                _flatten(item, child)
            )

    else:
        result[prefix] = value

    return result


def _number(value: Any) -> Optional[float]:

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):

        match = re.search(
            r"(?<![\d.])[-+]?\d+(?:\.\d+)?",
            value,
        )

        if match:

            try:
                return float(match.group(0))
            except ValueError:
                pass

    return None


def _first(
    *sources: Dict[str, Any],
    names: Iterable[str],
) -> Any:

    for name in names:

        for source in sources:

            value = source.get(name)

            if value is not None:
                return value

    return None


# ---------------------------------------------------------------------------
# Resolver numeric extraction
# ---------------------------------------------------------------------------

def _numeric_field(
    resolution: Any,
    names: Iterable[str],
) -> Optional[float]:

    flat = _flatten(
        _plain(resolution)
    )

    wanted = {
        str(name)
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
        for name in names
    }

    # Exact field match first.
    for key, value in flat.items():

        number = _number(value)

        if number is None:
            continue

        component = key.split(".")[-1]

        component = (
            component
            .split("[", 1)[0]
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        if component in wanted:
            return number

    # Then fuzzy field match.
    for key, value in flat.items():

        number = _number(value)

        if number is None:
            continue

        normalized = (
            key
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        if any(
            name in normalized
            for name in wanted
        ):
            return number

    return None


# ---------------------------------------------------------------------------
# Resolver rule/source extraction
# ---------------------------------------------------------------------------

def _walk_rule_records(
    value: Any,
) -> Iterable[
    Tuple[
        Optional[str],
        str,
        Dict[str, Any],
    ]
]:

    if isinstance(value, dict):

        rule_id = (
            value.get("regulation_id")
            or value.get("rule_id")
            or value.get("id")
            or value.get("regulation")
        )

        text_parts: List[str] = []

        for key in (
            "name",
            "title",
            "description",
            "source",
            "source_text",
            "markdown",
            "text",
            "result",
            "reason",
        ):

            if value.get(key) is not None:

                text_parts.append(
                    str(value[key])
                )

        if text_parts:

            yield (
                (
                    str(rule_id)
                    if rule_id is not None
                    else None
                ),
                "\n".join(text_parts),
                value,
            )

        for item in value.values():

            yield from _walk_rule_records(
                item
            )

        return

    if isinstance(value, (list, tuple)):

        for item in value:

            yield from _walk_rule_records(
                item
            )

        return

    if value is None:
        return

    if isinstance(value, str):

        match = re.search(
            r"(?:regulation_id|rule_id|id)"
            r"[=: ]+[\"']?"
            r"([0-9]+(?:\.[0-9]+)+)",
            value,
            flags=re.I,
        )

        yield (
            match.group(1)
            if match
            else None,
            value,
            {"raw": value},
        )

        return

    text = str(value)

    yield (
        None,
        text,
        {"raw": text},
    )


def _rule_text(
    resolution: Any,
    rule_ids: Iterable[str],
) -> List[Dict[str, Any]]:

    wanted = {
        str(x).strip()
        for x in rule_ids
    }

    records: List[Dict[str, Any]] = []

    for rule_id, text, raw in _walk_rule_records(
        resolution
    ):

        if (
            rule_id is None
            or rule_id in wanted
        ):

            records.append(
                {
                    "regulation_id": rule_id,
                    "text": text,
                    "raw": raw,
                }
            )

    return records


# ---------------------------------------------------------------------------
# FSI extraction from PostgreSQL source
# ---------------------------------------------------------------------------

def _extract_fsi_from_rule_text(
    records: List[Dict[str, Any]],
    road_width_m: Optional[float],
) -> FSIConstraints:

    result = FSIConstraints()

    for record in records:

        text = record["text"]

        lower = text.lower()

        if "table 6-g" not in lower:
            continue

        # Example DB row:
        #
        # | 15.0 m and above but below 24.0 m |
        # | 1.10 | 0.50 | 0.90 | 2.50 |
        #
        markdown_rows = re.findall(
            r"\|\s*"
            r"(\d+(?:\.\d+)?)"
            r"\s*m\s*and\s*above"
            r"\s*(?:but\s*)?(?:below|to\s*below)"
            r"\s*(\d+(?:\.\d+)?)"
            r"\s*m\s*\|"
            r"\s*(\d+(?:\.\d+)?)"
            r"\s*\|"
            r"\s*(\d+(?:\.\d+)?)"
            r"\s*\|"
            r"\s*(\d+(?:\.\d+)?)"
            r"\s*\|"
            r"\s*(\d+(?:\.\d+)?)"
            r"\s*\|",
            text,
            flags=re.I,
        )

        for (
            low,
            high,
            basic,
            premium,
            tdr,
            maximum,
        ) in markdown_rows:

            low_f = float(low)
            high_f = float(high)

            if (
                road_width_m is not None
                and low_f
                <= road_width_m
                < high_f
            ):

                result.basic_fsi = float(basic)
                result.premium_fsi = float(premium)

                result.maximum_tdr_loading = float(
                    tdr
                )

                result.maximum_building_potential = float(
                    maximum
                )

                result.maximum_fsi = float(
                    maximum
                )

                result.permissible_fsi = float(
                    maximum
                )

                result.basis = (
                    "PostgreSQL Table 6-G row selected "
                    f"for road width "
                    f"{road_width_m:g} m."
                )

                if record["regulation_id"]:

                    result.source_rule_ids.append(
                        record["regulation_id"]
                    )

                return result

    return result


# ---------------------------------------------------------------------------
# Site
# ---------------------------------------------------------------------------

def _build_site_constraints(
    image: Dict[str, Any],
    facts: Dict[str, Any],
    user: Dict[str, Any],
) -> SiteConstraints:

    def value(*names: str) -> Any:

        return _first(
            image,
            facts,
            user,
            names=names,
        )

    side_lengths = (
        value("plot_side_lengths")
        or {}
    )

    if isinstance(side_lengths, dict):

        normalized_side_lengths = {}

        for key, value_item in side_lengths.items():

            number = _number(value_item)

            if number is not None:

                normalized_side_lengths[
                    str(key)
                ] = number

    else:
        normalized_side_lengths = {}

    road_widths = value(
        "road_widths"
    )

    if isinstance(road_widths, list):

        normalized_road_widths = []

        for item in road_widths:

            number = _number(item)

            if number is not None:

                normalized_road_widths.append(
                    number
                )

    else:

        normalized_road_widths = []

    road_frontage_count = _number(
        value("road_frontage_count")
    )

    return SiteConstraints(

        plot_area_m2=_number(
            value("plot_area")
        ),

        plot_width_m=_number(
            value("plot_width")
        ),

        plot_depth_m=_number(
            value("plot_depth")
        ),

        plot_shape=value(
            "plot_shape"
        ),

        plot_side_lengths_m=(
            normalized_side_lengths
        ),

        survey_number=value(
            "survey_number"
        ),

        plot_number=value(
            "plot_number"
        ),

        road_width_m=_number(
            value("road_width")
        ),

        road_widths_m=(
            normalized_road_widths
        ),

        road_name=value(
            "road_name",
            "dp_road_name",
        ),

        road_frontage_count=(
            int(road_frontage_count)
            if road_frontage_count is not None
            else None
        ),

        access_width_m=_number(
            value("access_width")
        ),

        north_direction=value(
            "north_direction"
        ),

        scale=value(
            "scale"
        ),
    )


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def build_design_constraints(
    *,
    image_facts: Optional[Dict[str, Any]],
    planning_facts: Any,
    user_inputs: Optional[Dict[str, Any]],
    resolution: Any,
    selected_regulation_ids: Optional[
        List[str]
    ] = None,
    floor_height_assumption_m: float = 2.85,
) -> DesignConstraints:

    image = dict(
        image_facts or {}
    )

    facts = dict(
        _plain(planning_facts) or {}
    )

    user = dict(
        user_inputs or {}
    )

    rule_ids = list(
        selected_regulation_ids or []
    )

    def value(*names: str) -> Any:

        return _first(
            image,
            facts,
            user,
            names=names,
        )

    # -----------------------------------------------------------------------
    # Site
    # -----------------------------------------------------------------------

    site = _build_site_constraints(
        image,
        facts,
        user,
    )

    # -----------------------------------------------------------------------
    # Building program
    # -----------------------------------------------------------------------

    requested_units = _number(
        value("requested_units")
    )

    requested_floors = _number(
        value("requested_floors")
    )

    program = BuildingProgram(

        project_type=value(
            "project_type"
        ),

        development_type=value(
            "development_type"
        ),

        building_use=value(
            "building_use"
        ),

        building_type=value(
            "building_type"
        ),

        occupancy_type=value(
            "occupancy_type",
            "occupancy",
        ),

        requested_units=(
            int(requested_units)
            if requested_units is not None
            else None
        ),

        requested_unit_mix=(
            value("requested_unit_mix")
            or []
        ),

        requested_unit_area=(
            value("requested_unit_area")
            or {}
        ),

        allow_stilt_parking=value(
            "allow_stilt_parking"
        ),

        avoid_basement=value(
            "avoid_basement"
        ),
    )

    # -----------------------------------------------------------------------
    # Design objectives
    # -----------------------------------------------------------------------

    objectives = DesignObjectives(

        maximize_fsi=value(
            "maximize_fsi"
        ),

        maximize_parking=value(
            "maximize_parking"
        ),

        maximize_usable_area=value(
            "maximize_usable_area"
        ),

        optimize_daylight=value(
            "optimize_daylight"
        ),

        optimize_ventilation=value(
            "optimize_ventilation"
        ),

        optimize_orientation=value(
            "optimize_orientation"
        ),

        preferred_orientation=value(
            "preferred_orientation"
        ),

        design_objective=value(
            "design_objective"
        ),
    )

    # -----------------------------------------------------------------------
    # PostgreSQL regulatory evidence
    # -----------------------------------------------------------------------

    records = _rule_text(
        resolution,
        rule_ids,
    )

    # -----------------------------------------------------------------------
    # FSI
    # -----------------------------------------------------------------------

    fsi = _extract_fsi_from_rule_text(
        records,
        site.road_width_m,
    )

    if (
        fsi.permissible_fsi is not None
        and site.plot_area_m2 is not None
    ):

        fsi.permissible_floor_area_m2 = (
            site.plot_area_m2
            * fsi.permissible_fsi
        )

    # -----------------------------------------------------------------------
    # Height
    # -----------------------------------------------------------------------

    height = HeightConstraints(

        requested_height_m=_number(
            value("preferred_building_height")
        ),

        requested_floors=(
            int(requested_floors)
            if requested_floors is not None
            else None
        ),

        floor_height_assumption_m=(
            floor_height_assumption_m
        ),
    )

    resolved_height = _numeric_field(
        resolution,
        [
            "maximum_building_height",
            "permissible_building_height",
            "maximum_height",
            "max_height",
        ],
    )

    if resolved_height is not None:

        height.maximum_height_m = (
            resolved_height
        )

    height.source_rule_ids = [
        record["regulation_id"]
        for record in records
        if (
            record["regulation_id"]
            and record["regulation_id"]
            in rule_ids
            and "height"
            in record["text"].lower()
        )
    ]

    # -----------------------------------------------------------------------
    # Parking
    # -----------------------------------------------------------------------

    parking = ParkingConstraints(

        parking_mode=value(
            "parking_mode"
        ),

        requested_units=(
            program.requested_units
        ),

        unit_mix=(
            program.requested_unit_mix
        ),
    )

    parking.required_spaces = _numeric_field(
        resolution,
        [
            "required_parking",
            "parking_required",
            "required_car_parking",
            "parking_spaces_required",
            "required_parking_spaces",
        ],
    )

    parking.source_rule_ids = [
        record["regulation_id"]
        for record in records
        if (
            record["regulation_id"]
            and record["regulation_id"]
            in rule_ids
            and "parking"
            in record["text"].lower()
        )
    ]

    if parking.required_spaces is not None:

        parking.status = "RESOLVED"

    else:

        parking.status = "NOT_RESOLVED"

    # -----------------------------------------------------------------------
    # Setbacks
    # -----------------------------------------------------------------------

    setback_rule_ids = [
        record["regulation_id"]
        for record in records
        if (
            record["regulation_id"]
            and record["regulation_id"]
            in rule_ids
            and (
                "setback"
                in record["text"].lower()
                or "marginal distance"
                in record["text"].lower()
                or "margin"
                in record["text"].lower()
            )
        )
    ]

    setbacks = SetbackConstraints(
        source_rule_ids=setback_rule_ids,
    )

    if setback_rule_ids:

        setbacks.status = (
            "SOURCE_AVAILABLE_REQUIRES_INTERPRETATION"
        )

    # IMPORTANT:
    # We deliberately do not invent setback numbers.
    # A later deterministic geometry/rule interpreter should parse the
    # applicable setback table from the PostgreSQL source.

    # -----------------------------------------------------------------------
    # Access
    # -----------------------------------------------------------------------

    access_rule_ids = [
        record["regulation_id"]
        for record in records
        if (
            record["regulation_id"]
            and record["regulation_id"]
            in rule_ids
            and (
                "access"
                in record["text"].lower()
                or "fire"
                in record["text"].lower()
                or "road width"
                in record["text"].lower()
            )
        )
    ]

    access = AccessConstraints(

        road_width_m=(
            site.road_width_m
        ),

        access_width_m=(
            site.access_width_m
        ),

        source_rule_ids=(
            access_rule_ids
        ),
    )

    # -----------------------------------------------------------------------
    # Unresolved fields
    # -----------------------------------------------------------------------

    unresolved_constraints: List[str] = []

    warnings: List[str] = []

    if fsi.permissible_fsi is None:

        unresolved_constraints.append(
            "permissible_fsi"
        )

    if height.maximum_height_m is None:

        unresolved_constraints.append(
            "maximum_building_height"
        )

    if parking.required_spaces is None:

        unresolved_constraints.append(
            "required_parking"
        )

    if not setback_rule_ids:

        unresolved_constraints.append(
            "setbacks"
        )

    # -----------------------------------------------------------------------
    # Preserve regulatory source/evidence
    # -----------------------------------------------------------------------

    regulatory_rules = []

    for record in records:

        if (
            record["regulation_id"]
            not in rule_ids
        ):
            continue

        regulatory_rules.append(
            {
                "regulation_id": (
                    record["regulation_id"]
                ),
                "source_text": record["text"],
            }
        )

    if not records and rule_ids:

        warnings.append(
            "Selected PostgreSQL regulation IDs were supplied, "
            "but no textual rule records could be interpreted by "
            "planning_to_design."
        )

    return DesignConstraints(

        site=site,

        program=program,

        fsi=fsi,

        height=height,

        setbacks=setbacks,

        parking=parking,

        access=access,

        objectives=objectives,

        regulatory_rules=(
            regulatory_rules
        ),

        unresolved_constraints=(
            unresolved_constraints
        ),

        warnings=warnings,
    )


def planning_to_design(
    planning_facts: Any,
    user_inputs: Optional[Dict[str, Any]],
    resolution: Any,
    *,
    image_facts: Optional[
        Dict[str, Any]
    ] = None,
    selected_regulation_ids: Optional[
        List[str]
    ] = None,
    floor_height_assumption_m: float = 2.85,
) -> DesignConstraints:

    return build_design_constraints(

        image_facts=image_facts,

        planning_facts=planning_facts,

        user_inputs=user_inputs,

        resolution=resolution,

        selected_regulation_ids=(
            selected_regulation_ids
        ),

        floor_height_assumption_m=(
            floor_height_assumption_m
        ),
    )