from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from townplanning.modules.planning.domain.planning_facts import PlanningFacts
from townplanning.modules.planning.regulations.udcpr_rule_resolver import UDCPRRuleResolver
from townplanning.infrastructure.database.session import SessionLocal
from townplanning.modules.regulations.extraction.postgresql_authoritative_table_resolver import (
    PostgreSQLAuthoritativeTableResolver,
)
from townplanning.modules.vision.services.general_vision_service import (
    GeneralVisionService,
)
from townplanning.modules.vision.services.vision_planning_mapper import (
    VisionPlanningMapper,
)


# =============================================================================
# PURPOSE
# =============================================================================
#
# This is the vision -> planning -> design-input test built on the successful
# deterministic PostgreSQL rule-graph test.
#
# IMPORTANT:
#   * Image AI extracts OBSERVED site facts only.
#   * User JSON supplies project/program facts, including the explicit
#     tenement_carpet_areas list.
#   * PostgreSQLAuthoritativeTableResolver is authoritative for regulatory values.
#   * Rules are evaluated repeatedly until no new deterministic fact is written.
#   * The drawing layer receives the COMPLETE deterministic planning state,
#     rule metadata, missing inputs, approvals/NOCs, site facts and the unit
#     program. No regulatory number is invented in this test.
#
# Usage:
#   python tests/functional/planning/test_vision_to_planning.py \
#       --image tests/functional/vision/data/sample1.png \
#       --user-input-file user_input.json
#
# =============================================================================

REGULATORY_FIELDS = PlanningFacts.regulatory_value_fields()
REGULATORY_FIELDS |= {
    "height_approval_required",
    "height_limit_basis",
    "fire_approval_status",
    "fire_approval_authority",
    "fire_approved_height_source",
}
DRAWING_STAGE_FIELDS = {
    "fire_access_required",
    "ramp_required",
    "ramp_width_m",
    "ramp_gradient",
    "maximum_travel_distance",
}

# Use the same regulatory field contract exposed by PlanningFacts.
# Do not duplicate the field list in this test.
AUTHORITATIVE_CONSTRAINT_FIELDS = set(
    PlanningFacts.regulatory_value_fields()
)

# Retrieval categories are optional in UDCPRRuleResolver's Chroma API.
# Passing None lets the resolver build its normal semantic query from the
# PlanningFacts instead of maintaining a second hardcoded category list here.
AUTHORITATIVE_RETRIEVAL_CATEGORIES: list[str] | None = None


def authoritative_requested_fields(
    facts: PlanningFacts,
) -> list[str]:
    """Return applicable deterministic fields from the PlanningFacts contract.

    The test does not hardcode regulation/table identifiers. Fields come from
    PlanningFacts.regulatory_value_fields(). Building separation is conditional
    because it only applies when more than one building is being designed.
    """

    fields = set(AUTHORITATIVE_CONSTRAINT_FIELDS)

    number_of_buildings = getattr(
        facts,
        "number_of_buildings",
        None,
    )

    if "building_separation" in fields:
        try:
            if number_of_buildings is None or int(number_of_buildings) <= 1:
                fields.discard("building_separation")
        except (TypeError, ValueError):
            fields.discard("building_separation")

    return sorted(fields)




def _derive_tenement_carpet_areas(
    user_input: dict[str, Any],
) -> None:
    """
    Derive tenement_carpet_areas from requested_unit_area and
    requested_unit_mix.

    requested_unit_area:
        {
            "2BHK": 780.0,
            "3BHK": 1020.0
        }

    requested_unit_mix:
        [
            {"type": "2BHK", "count": 6},
            {"type": "3BHK", "count": 6}
        ]

    Result:
        tenement_carpet_areas =
            [780.0 x 6, 1020.0 x 6]

    This is derived from the user's requested unit areas. It does not
    hardcode BHK types, areas, counts, or UDCPR rules.
    """

    requested_unit_area = user_input.get("requested_unit_area")
    requested_unit_mix = user_input.get("requested_unit_mix")

    if not isinstance(requested_unit_area, dict):
        return

    if not isinstance(requested_unit_mix, list):
        return

    tenement_carpet_areas: list[float] = []

    for unit in requested_unit_mix:
        if not isinstance(unit, dict):
            continue

        unit_type = unit.get("type")
        count = unit.get("count")

        if unit_type is None or count is None:
            continue

        area = requested_unit_area.get(unit_type)

        if area is None:
            continue

        try:
            count = int(count)
            area = float(area)
        except (TypeError, ValueError):
            continue

        if count <= 0 or area <= 0:
            continue

        tenement_carpet_areas.extend(
            [area] * count
        )

    if not tenement_carpet_areas:
        return

    user_input["tenement_carpet_areas"] = (
        tenement_carpet_areas
    )

    # Preserve the unit supplied by the user.
    # Default only when it is absent.
    user_input["tenement_carpet_area_unit"] = (
        user_input.get(
            "tenement_carpet_area_unit",
            "sqft",
        )
    )

# =============================================================================
# INPUT / IMAGE EXTRACTION
# =============================================================================

def load_user_input(path: str | None) -> dict[str, Any]:
    input_path = Path(path or "user_input.json")
    if not input_path.exists():
        raise FileNotFoundError(f"User input file not found: {input_path}")

    loaded = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("user_input.json must contain a JSON object")

    return loaded


def _image_data_url(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


# These are OBSERVED site/plot fields. They are not regulatory constraints.
# OpenAI is used only when the existing vision pipeline leaves core plot
# information unresolved. Existing non-null VisionService values are never
# overwritten by the fallback.
_OPENAI_PLOT_FIELDS = (
    "plot_area",
    "plot_width",
    "plot_depth",
    "road_width",
    "north_direction",
)

_OPENAI_PLOT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "plot_area": {"type": ["number", "null"]},
        "plot_width": {"type": ["number", "null"]},
        "plot_depth": {"type": ["number", "null"]},
        "road_width": {"type": ["number", "null"]},
        "north_direction": {"type": ["string", "null"]},
    },
    "required": list(_OPENAI_PLOT_FIELDS),
}


def _openai_plot_fallback(
    image_path: Path,
    current_facts: PlanningFacts,
) -> dict[str, Any]:
    """Recover missing core plot/site observations with one OpenAI vision call.

    This function is intentionally a fallback, not a second normal vision
    pipeline. It is called only when the existing GeneralVisionService +
    VisionPlanningMapper did not provide all core plot fields.

    The model is explicitly forbidden from producing regulatory conclusions.
    """

    missing = [
        field
        for field in _OPENAI_PLOT_FIELDS
        if getattr(current_facts, field, None) is None
    ]

    if not missing:
        return {}

    if OpenAI is None:
        raise RuntimeError(
            "OpenAI SDK is required only for the plot-information fallback: "
            "pip install -U openai"
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set; it is required because the existing "
            "vision pipeline did not extract the core plot information."
        )

    client = OpenAI(api_key=api_key)

    prompt = f"""
Read this site/building drawing ONLY for the following missing, visibly
stated plot/site facts:

{json.dumps(missing)}

Rules:
- Extract only information visibly stated/readable in the image.
- Do not infer or calculate regulatory values.
- Do not calculate FSI, setbacks, coverage, parking, height limits,
  fire/lift/stair requirements, approvals, or any other regulation.
- Do not invent a value.
- Return null when a requested value is absent or unreadable.
- Do not overwrite or reconsider values that are not requested.
- For dimensions, return the numeric value exactly as visibly labelled.
- plot_area must be the explicitly stated plot/site area, if present.
- plot_width and plot_depth must be explicitly stated dimensions, if present.
- road_width must be the explicitly stated road width, if present.
- north_direction must be the visibly stated north direction/label, if present.
- Do not derive plot_area from plot_width and plot_depth.
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": _image_data_url(image_path),
                    },
                ],
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "missing_plot_facts",
                "strict": True,
                "schema": _OPENAI_PLOT_SCHEMA,
            }
        },
    )

    raw = json.loads(response.output_text)

    # Only accept fields that were missing before the fallback call.
    return {
        field: raw.get(field)
        for field in missing
        if raw.get(field) is not None
    }


def extract_image_facts(
    image_path: str | Path,
    general_vision: GeneralVisionService,
):
    """Use GeneralVisionService first; conditionally recover missing plot data."""
    path = Path(image_path)

    evidence = general_vision.analyze(path)

    mapper = VisionPlanningMapper()
    mapping_result = mapper.map(
        PlanningFacts(),
        evidence,
    )

    if mapping_result is None or not hasattr(mapping_result, "facts"):
        raise RuntimeError(
            "VisionPlanningMapper did not return a result containing .facts."
        )

    facts = mapping_result.facts
    if isinstance(facts, dict):
        facts = PlanningFacts(**facts)

    if not isinstance(facts, PlanningFacts):
        raise RuntimeError(
            "VisionPlanningMapper result.facts is not PlanningFacts: "
            f"{type(facts).__name__}"
        )

    fallback_fields: dict[str, Any] = {}

    # IMPORTANT: OpenAI is NOT called when the normal vision pipeline has
    # already extracted the core plot information.
    missing_plot_fields = [
        field
        for field in _OPENAI_PLOT_FIELDS
        if getattr(facts, field, None) is None
    ]

    if missing_plot_fields:
        fallback_fields = _openai_plot_fallback(
            path,
            facts,
        )

        # Apply only values that were missing. Never replace an existing
        # GeneralVisionService value with an OpenAI value.
        for field, value in fallback_fields.items():
            if (
                value is not None
                and getattr(facts, field, None) is None
            ):
                setattr(facts, field, value)
                facts.fact_sources[field] = "openai_plot_fallback"

        facts.normalize()

    mapping_info = {
        "mapped_fields": getattr(mapping_result, "mapped_fields", []),
        "image_regulatory_fields": getattr(
            mapping_result, "image_regulatory_fields", []
        ),
        "image_project_fields": getattr(
            mapping_result, "image_project_fields", []
        ),
        "ignored_regulatory_text": getattr(
            mapping_result, "ignored_regulatory_text", []
        ),
        "evidence": getattr(mapping_result, "evidence", {}),
        "openai_plot_fallback_used": bool(missing_plot_fields),
        "openai_plot_fallback_fields": sorted(fallback_fields),
        "openai_plot_fields_missing_before_fallback": missing_plot_fields,
    }

    return facts, evidence, mapping_info


def _normalize_chroma_regulation_id(value: Any) -> str:
    """Convert an existing Chroma regulation identifier to PostgreSQL form."""
    raw = str(value or "").strip()
    if raw.upper().startswith("UDCPR:"):
        raw = raw[len("UDCPR:"):]
    if "|" in raw:
        raw = raw.split("|", 1)[0]
    return raw.strip()


def retrieve_chroma_evidence(
    facts: PlanningFacts,
    *,
    top_k: int = 100,
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    """Use the existing UDCPRRuleResolver Chroma path.

    UDCPRRuleResolver is the project's existing Chroma integration. Its own
    candidate-ID method is used so this test does not duplicate Chroma query,
    embedding, score-threshold, or regulation-ID extraction logic.

    The Chroma documents are then passed as evidence to
    PostgreSQLAuthoritativeTableResolver. Chroma is retrieval evidence only;
    PostgreSQL remains authoritative for table selection and regulatory values.
    """
    resolver = UDCPRRuleResolver()

    collection = getattr(resolver, "_chroma_collection", None)
    embedding_service = getattr(resolver, "_embedding_service", None)

    if collection is None:
        raise RuntimeError(
            "UDCPRRuleResolver did not initialize its Chroma collection. "
            "Check CHROMA_PATH and CHROMA_COLLECTION."
        )
    if embedding_service is None:
        raise RuntimeError(
            "UDCPRRuleResolver did not initialize its project embedding service."
        )

    categories = AUTHORITATIVE_RETRIEVAL_CATEGORIES

    # Use the resolver's own Chroma candidate-ID logic.
    candidate_regulations = resolver._chroma_candidate_regulation_ids(
        facts=facts,
        categories=categories,
        top_k=top_k,
    )

    retrieval_report: dict[str, Any] = {
        "path": getattr(resolver, "chroma_path", None),
        "collection": getattr(resolver, "chroma_collection_name", None),
        "documents": collection.count(),
        "categories": categories or "resolver_default_semantic_query",
        "candidate_regulations": list(candidate_regulations),
        "matches": [],
    }

    if not candidate_regulations:
        return [], [], retrieval_report

    # Reuse the exact semantic query builder used by UDCPRRuleResolver.
    query = resolver._build_chroma_query(
        facts=facts,
        categories=categories,
    )
    embedding = embedding_service.embed_query(query)

    if not isinstance(embedding, (list, tuple)):
        raise RuntimeError(
            "UDCPRRuleResolver embedding service returned an invalid embedding."
        )

    result = collection.query(
        query_embeddings=[list(embedding)],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    candidate_set = {str(value).strip() for value in candidate_regulations}
    best_by_regulation: dict[str, dict[str, Any]] = {}

    for index, chroma_id in enumerate(ids):
        metadata = (
            metadatas[index]
            if index < len(metadatas) and isinstance(metadatas[index], dict)
            else {}
        )
        document = documents[index] if index < len(documents) else ""
        distance = distances[index] if index < len(distances) else None

        raw_regulation_id = None
        extract_id = getattr(resolver, "_extract_chroma_regulation_id", None)
        if callable(extract_id):
            raw_regulation_id = extract_id(metadata)
        if raw_regulation_id is None:
            raw_regulation_id = chroma_id

        regulation_number = _normalize_chroma_regulation_id(raw_regulation_id)
        if regulation_number not in candidate_set:
            continue

        # Never manufacture source text. Prefer explicit source text in Chroma
        # metadata; otherwise use the Chroma document payload.
        source_text = str(
            metadata.get("source_text")
            or metadata.get("text")
            or metadata.get("content")
            or metadata.get("page_content")
            or document
            or ""
        ).strip()
        if not source_text:
            continue

        source_type = str(
            metadata.get("source_type")
            or metadata.get("type")
            or "paragraph"
        ).strip() or "paragraph"

        evidence = {
            "regulation_number": regulation_number,
            "source_type": source_type,
            "source_text": source_text,
            "chroma_id": str(chroma_id),
            "distance": distance,
            "metadata": metadata,
            "query": query,
        }

        previous = best_by_regulation.get(regulation_number)
        if previous is None:
            best_by_regulation[regulation_number] = evidence
        else:
            previous_distance = previous.get("distance")
            if (
                distance is not None
                and (
                    previous_distance is None
                    or float(distance) < float(previous_distance)
                )
            ):
                best_by_regulation[regulation_number] = evidence

    # Preserve the ordering produced by UDCPRRuleResolver's Chroma retrieval.
    sources = [
        best_by_regulation[regulation_id]
        for regulation_id in candidate_regulations
        if regulation_id in best_by_regulation
    ]

    missing_evidence = [
        regulation_id
        for regulation_id in candidate_regulations
        if regulation_id not in best_by_regulation
    ]
    if missing_evidence:
        raise RuntimeError(
            "Chroma returned regulation candidates without source documents: "
            + ", ".join(missing_evidence)
        )

    retrieval_report["query"] = query
    retrieval_report["matches"] = [
        {
            "regulation_number": source["regulation_number"],
            "chroma_id": source["chroma_id"],
            "distance": source.get("distance"),
            "source_type": source.get("source_type"),
        }
        for source in sources
    ]

    return list(candidate_regulations), sources, retrieval_report


def build_selected_regulatory_sources(
    facts: PlanningFacts,
    *,
    top_k: int,
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    """Build regulatory evidence directly from the existing UDCPR Chroma path.

    No regulation ID or regulatory paragraph is hard-coded here.
    PostgreSQLAuthoritativeTableResolver remains authoritative.
    """
    return retrieve_chroma_evidence(facts, top_k=top_k)



def _authoritative_constraint_map(resolution: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for constraint in getattr(resolution, "constraints", []) or []:
        key = str(getattr(constraint, "key", "")).strip()
        if not key:
            continue
        result[key] = {
            "value": getattr(constraint, "value", None),
            "unit": getattr(constraint, "unit", None),
            "source_rule_id": getattr(constraint, "source_rule_id", None),
            "regulation_id": getattr(constraint, "regulation_id", None),
            "rule_name": getattr(constraint, "rule_name", None),
            "category": getattr(constraint, "category", None),
            "status": getattr(constraint, "status", None),
            "reason": getattr(constraint, "reason", None),
            "metadata": getattr(constraint, "metadata", {}) or {},
        }
    return result


def _apply_authoritative_constraints(
    facts: PlanningFacts,
    resolution: Any,
) -> list[str]:
    """Copy resolver-produced values into PlanningFacts without calculation."""
    changed: list[str] = []
    setter = getattr(facts, "set_resolved_value", None)
    if not callable(setter):
        raise RuntimeError(
            "PlanningFacts.set_resolved_value() is required for authoritative "
            "PostgreSQL constraint integration."
        )

    for constraint in getattr(resolution, "constraints", []) or []:
        field = str(getattr(constraint, "key", "")).strip()
        value = getattr(constraint, "value", None)
        if field not in AUTHORITATIVE_CONSTRAINT_FIELDS or value is None:
            continue

        before = getattr(facts, field, None)
        setter(
            field,
            value,
            rule_id=getattr(constraint, "source_rule_id", None),
            regulation_id=getattr(constraint, "regulation_id", None),
            unit=getattr(constraint, "unit", None),
            source="postgresql_authoritative_table_resolver",
        )
        after = getattr(facts, field, None)
        if before != after:
            changed.append(field)

    return changed


def _serialize_selected_table(selection: Any) -> dict[str, Any]:
    return {
        "regulation_number": getattr(selection, "regulation_number", None),
        "table_number": getattr(selection, "table_number", None),
        "table_title": getattr(selection, "table_title", None),
        "reason": getattr(selection, "reason", None),
    }


def resolve_until_stable(
    facts: PlanningFacts,
    *,
    retrieval_passes: tuple[int, ...] = (10, 25, 50, 100),
) -> dict[str, Any]:
    """Resolve deterministic constraints using progressively larger evidence.

    Each retrieval window is tried only until the currently applicable
    deterministic answer is complete. The OpenAI regulatory extractor remains
    inside PostgreSQLAuthoritativeTableResolver; this test only controls how
    much ranked Chroma evidence is supplied to it.
    """
    requested_fields = authoritative_requested_fields(facts)
    if not requested_fields:
        raise RuntimeError(
            "No applicable deterministic PlanningFacts fields found."
        )

    all_passes: list[dict[str, Any]] = []
    final_resolution = None
    final_constraints: dict[str, Any] = {}
    selected_regulations: list[str] = []
    selected_sources: list[dict[str, Any]] = []
    chroma_retrieval: dict[str, Any] = {}
    all_changed: set[str] = set()

    for top_k in retrieval_passes:
        (
            selected_regulations,
            selected_sources,
            chroma_retrieval,
        ) = build_selected_regulatory_sources(
            facts,
            top_k=top_k,
        )

        if not selected_regulations:
            all_passes.append({
                "retrieval_top_k": top_k,
                "status": "NO_CHROMA_CANDIDATES",
                "changed_fields": [],
                "constraint_values": {},
                "selected_regulations": [],
                "selected_tables": [],
                "warnings": [
                    "No Chroma candidate regulations returned."
                ],
                "errors": [],
                "missing_inputs": [],
            })
            continue

        db = SessionLocal()
        try:
            resolver = PostgreSQLAuthoritativeTableResolver(db)
            final_resolution = resolver.resolve(
                facts=facts,
                selected_regulations=selected_regulations,
                chroma_sources=selected_sources,
                requested_fields=requested_fields,
            )
        finally:
            db.close()

        changed = _apply_authoritative_constraints(
            facts,
            final_resolution,
        )
        all_changed.update(changed)

        constraint_values = _authoritative_constraint_map(
            final_resolution
        )
        final_constraints.update(constraint_values)

        selected_tables = [
            _serialize_selected_table(selection)
            for selection in getattr(
                final_resolution,
                "selections",
                [],
            ) or []
        ]

        unresolved = [
            field
            for field in requested_fields
            if getattr(facts, field, None) is None
            and field not in final_constraints
        ]

        all_passes.append({
            "retrieval_top_k": top_k,
            "status": getattr(final_resolution, "status", None),
            "changed_fields": changed,
            "constraint_values": constraint_values,
            "selected_regulations": list(selected_regulations),
            "selected_tables": selected_tables,
            "warnings": list(
                getattr(final_resolution, "warnings", []) or []
            ),
            "errors": list(
                getattr(final_resolution, "errors", []) or []
            ),
            "missing_inputs": list(
                getattr(final_resolution, "missing_inputs", []) or []
            ),
            "unresolved_requested_fields": unresolved,
        })

        # Stop immediately once the requested deterministic answer is complete.
        if not unresolved:
            break

    if final_resolution is None:
        raise RuntimeError(
            "PostgreSQL authoritative resolution did not execute."
        )

    # User-requested deterministic derivation:
    # maximum storeys = maximum height / 3 m.
    maximum_height = getattr(facts, "maximum_height_m", None)
    if (
        maximum_height is not None
        and getattr(facts, "maximum_storeys", None) is None
    ):
        try:
            maximum_storeys = int(float(maximum_height) // 3.0)
            facts.set_resolved_value(
                "maximum_storeys",
                maximum_storeys,
                calculation=(
                    "maximum_height_m / 3.0 m floor-height convention"
                ),
                source="deterministic_derived_from_udcpr_height",
            )
            final_constraints["maximum_storeys"] = maximum_storeys
        except (TypeError, ValueError):
            pass

    # User-requested ground-coverage derivation:
    # for a rectangular plot, subtract canonical left/right and front/rear
    # setbacks from the corresponding plot dimensions.
    plot_width = getattr(facts, "plot_width", None)
    plot_depth = getattr(facts, "plot_depth", None)
    front = getattr(facts, "front_setback", None)
    rear = getattr(facts, "rear_setback", None)
    left = getattr(facts, "side_setback_left", None)
    right = getattr(facts, "side_setback_right", None)

    if all(
        value is not None
        for value in (
            plot_width,
            plot_depth,
            front,
            rear,
            left,
            right,
        )
    ):
        try:
            buildable_width = max(
                0.0,
                float(plot_width) - float(left) - float(right),
            )
            buildable_depth = max(
                0.0,
                float(plot_depth) - float(front) - float(rear),
            )
            coverage_area = buildable_width * buildable_depth

            facts.set_resolved_value(
                "maximum_ground_coverage",
                coverage_area,
                unit="m2",
                calculation=(
                    "buildable width = plot width - left/right setbacks; "
                    "buildable depth = plot depth - front/rear setbacks"
                ),
                source="deterministic_geometry_from_udcpr_setbacks",
            )
            final_constraints["maximum_ground_coverage"] = coverage_area
        except (TypeError, ValueError):
            pass

    # Drawing-stage values are deliberately not fabricated during regulatory
    # resolution. They become inputs to the later drawing phase.
    drawing_stage_constraints = {
        field: getattr(facts, field, None)
        for field in sorted(DRAWING_STAGE_FIELDS)
        if hasattr(facts, field)
    }

    missing_inputs = list(
        getattr(final_resolution, "missing_inputs", []) or []
    )
    warnings = list(
        getattr(final_resolution, "warnings", []) or []
    )
    errors = list(
        getattr(final_resolution, "errors", []) or []
    )

    for field in missing_inputs:
        facts.record_missing_input(
            str(field),
            reason=(
                "Required by authoritative regulatory evidence resolution."
            ),
        )

    facts.finalize_regulatory_resolution()

    if errors:
        status = "ERROR"
    elif final_constraints:
        status = "RESOLVED"
    else:
        status = getattr(
            final_resolution,
            "status",
            "INSUFFICIENT_RULE_DATA",
        )

    return {
        "passes": all_passes,
        "stable": bool(all_passes),
        "changed_fields": sorted(all_changed),
        "requested_fields": requested_fields,
        "selected_regulations": list(selected_regulations),
        "selected_evidence": selected_sources,
        "chroma_retrieval": chroma_retrieval,
        "selected_tables": [
            _serialize_selected_table(selection)
            for selection in getattr(
                final_resolution,
                "selections",
                [],
            ) or []
        ],
        "final_constraints": final_constraints,
        "missing_inputs": missing_inputs,
        "warnings": warnings,
        "errors": errors,
        "approval_requirements": [],
        "drawing_stage_constraints": drawing_stage_constraints,
        "resolver_status": status,
        "resolver": "PostgreSQLAuthoritativeTableResolver",
    }


# =============================================================================
# DESIGN PROGRAM / DRAWING INPUT
# =============================================================================

def build_facts(
    user_input: dict[str, Any],
    image_facts: dict[str, Any],
) -> tuple[PlanningFacts, dict[str, Any], dict[str, Any]]:
    """Build the canonical PlanningFacts from user input + vision observations.

    User input is authoritative for explicitly supplied project/program values.
    Image facts fill only fields that are absent from user input. A differing
    image observation is retained as a conflict rather than silently replacing
    user input.
    """

    facts = PlanningFacts()
    conflicts: dict[str, Any] = {}
    observed: dict[str, Any] = {}

    canonical = getattr(
        facts,
        "_canonical_field_name",
        lambda name: name,
    )

    def apply_value(
        field_name: str,
        value: Any,
        source: str,
        *,
        overwrite: bool = False,
    ) -> None:
        if value is None:
            return

        field = canonical(field_name)

        if not hasattr(facts, field):
            # Keep unknown vision/user keys visible for diagnostics, but do not
            # add arbitrary attributes to PlanningFacts.
            return

        existing = getattr(facts, field, None)

        if existing is None or overwrite:
            setattr(facts, field, value)

            if hasattr(facts, "fact_sources"):
                facts.fact_sources[field] = source
            return

        if existing != value:
            conflicts[field] = {
                "planning_facts_value": existing,
                "observed_value": value,
                "planning_facts_source": (
                    facts.fact_sources.get(field)
                    if hasattr(facts, "fact_sources")
                    else None
                ),
                "observed_source": source,
            }

    # --------------------------------------------------------------
    # 1. User/project inputs
    # --------------------------------------------------------------
    for field_name, value in user_input.items():
        if value is None:
            continue
        apply_value(
            field_name,
            value,
            "user_input",
            overwrite=True,
        )

    # --------------------------------------------------------------
    # 2. Vision observations
    # --------------------------------------------------------------
    for field_name, value in image_facts.items():
        if value is None:
            continue

        field = canonical(field_name)
        observed[field] = value

        # User input wins. Vision fills only missing canonical fields.
        apply_value(
            field,
            value,
            "vision",
            overwrite=False,
        )

    # --------------------------------------------------------------
    # 3. Keep tenement areas derived from requested unit areas.
    # --------------------------------------------------------------
    _derive_tenement_carpet_areas(user_input)

    requested_areas = user_input.get("requested_unit_area")
    if requested_areas:
        # Re-apply the derived program after canonical user fields have been
        # loaded, without requiring tenement_carpet_areas in user_input.json.
        apply_value(
            "tenement_carpet_areas",
            user_input.get("tenement_carpet_areas"),
            "derived_from_requested_unit_area",
            overwrite=True,
        )

        apply_value(
            "tenement_carpet_area_unit",
            user_input.get(
                "tenement_carpet_area_unit",
                "sqft",
            ),
            "derived_from_requested_unit_area",
            overwrite=True,
        )

    # --------------------------------------------------------------
    # 4. Normalize if the domain object exposes normalization.
    # --------------------------------------------------------------
    normalize = getattr(facts, "normalize", None)
    if callable(normalize):
        normalize()

    return facts, conflicts, observed


def _fact(facts: PlanningFacts, name: str, default: Any = None) -> Any:
    value = getattr(facts, name, None)
    if value is not None:
        return value
    values = getattr(facts, "values", None)
    if isinstance(values, dict):
        return values.get(name, default)
    return default


def _regulatory_value(facts: PlanningFacts, resolution: dict[str, Any], name: str) -> Any:
    value = _fact(facts, name)
    if value is not None:
        return value
    final_constraints = resolution.get("final_constraints") or {}
    return final_constraints.get(name) if isinstance(final_constraints, dict) else None


def build_tenement_program(facts: PlanningFacts) -> dict[str, Any]:
    raw = _fact(facts, "tenement_carpet_areas", [])
    areas = [float(v) for v in raw] if isinstance(raw, (list, tuple)) else []
    return {
        "unit_count": len(areas),
        "tenement_carpet_areas_m2": areas,
        "total_tenement_carpet_area_m2": sum(areas),
        "average_tenement_carpet_area_m2": (
            sum(areas) / len(areas) if areas else None
        ),
    }


def calculate_floor_plate_and_units_per_floor(
    facts: PlanningFacts,
    resolution: dict[str, Any],
    *,
    efficiency: float = 0.82,
    common_area_m2: float = 0.0,
) -> dict[str, Any]:
    """Calculate a preliminary program floor plate.

    If an exact buildable-envelope area is not present in PlanningFacts, this
    uses the program's gross-area requirement as the preliminary floor plate.
    It does NOT pretend this is the final architectural envelope; exact
    geometry still needs plot coordinates/polygon + setbacks.
    """
    if not (0 < efficiency <= 1):
        raise ValueError("efficiency must be > 0 and <= 1")

    program = build_tenement_program(facts)
    areas = program["tenement_carpet_areas_m2"]
    total_carpet = program["total_tenement_carpet_area_m2"]

    plot_area = _fact(facts, "plot_area")
    maximum_fsi = _regulatory_value(facts, resolution, "maximum_fsi")

    permissible_total_floor_area_m2 = None
    if isinstance(plot_area, (int, float)) and isinstance(maximum_fsi, (int, float)):
        permissible_total_floor_area_m2 = float(plot_area) * float(maximum_fsi)

    required_gross_total_m2 = total_carpet / efficiency + common_area_m2

    # This is a preliminary program plate. A later geometry layer can replace
    # it with the actual setback-derived buildable envelope without changing
    # the PostgreSQL resolver.
    preliminary_floor_plate_m2 = required_gross_total_m2
    fsi_feasible = (
        permissible_total_floor_area_m2 is None
        or required_gross_total_m2 <= permissible_total_floor_area_m2 + 1e-9
    )

    # If the required program is FSI-feasible and no physical envelope is yet
    # available, place the complete requested program on the preliminary plate.
    # This gives a deterministic baseline for the drawing layer. The geometry
    # layer is expected to split this into multiple floors once the envelope /
    # height constraints are available.
    units_per_floor = len(areas) if areas else 0
    number_of_floors = 1 if units_per_floor else 0

    return {
        "calculation_status": "preliminary_program_plate",
        "design_efficiency": efficiency,
        "design_common_area_m2": common_area_m2,
        "regulatory_plot_area_m2": plot_area,
        "regulatory_maximum_fsi": maximum_fsi,
        "regulatory_permissible_total_floor_area_m2": permissible_total_floor_area_m2,
        "user_unit_count": len(areas),
        "user_total_tenement_carpet_area_m2": total_carpet,
        "required_gross_total_area_m2": required_gross_total_m2,
        "preliminary_floor_plate_m2": preliminary_floor_plate_m2,
        "design_units_per_floor": units_per_floor,
        "design_estimated_number_of_floors": number_of_floors,
        "fsi_program_feasible": fsi_feasible,
        "geometry_note": (
            "Exact setback-derived floor plate requires plot polygon/coordinates "
            "and applicable height/geometry constraints; those are not inferred here."
        ),
    }


def build_drawing_design_input(
    facts: PlanningFacts,
    resolution: dict[str, Any],
    observed: dict[str, Any],
) -> dict[str, Any]:
    # Preserve every deterministic constraint, not only a fixed shortlist.
    final_constraints = resolution.get("final_constraints") or {}

    regulatory_values = {}
    for field in sorted(REGULATORY_FIELDS):
        value = _regulatory_value(facts, resolution, field)
        if value is not None:
            regulatory_values[field] = value

    site_fields = (
        "plot_area", "plot_width", "plot_depth", "plot_shape", "plot_side_lengths",
        "boundary", "road_width", "road_widths", "road_locations",
        "road_frontage_count", "road_type", "road_classification",
        "access_available", "access_width", "access_length", "road_name",
        "north_direction", "scale",
    )
    site = {name: _fact(facts, name) for name in site_fields if _fact(facts, name) is not None}

    design_constraints = {
        "all_final_constraint_values": final_constraints,
        "regulatory_values": regulatory_values,
        "applied_rules": resolution.get("all_applied_rules", []),
        "unresolved_rules": resolution.get("all_unresolved_rules", []),
        "rejected_rules": resolution.get("all_rejected_rules", []),
        "missing_inputs": resolution.get("missing_inputs", []),
        "approval_requirements": resolution.get("approval_requirements", []),
        "canonical_regulatory_facts": facts.to_dict(),
    }

    return {
        "site": site,
        "observed_drawing_facts": observed,
        "planning_constraints": design_constraints,
        "program": build_tenement_program(facts),
        "floor_plan": calculate_floor_plate_and_units_per_floor(facts, resolution),
    }


# =============================================================================
# MAIN TEST
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Vision -> PlanningFacts -> deterministic PostgreSQL rule graph "
            "-> complete drawing/design input test."
        )
    )
    parser.add_argument(
        "--image",
        action="append",
        dest="images",
        help="Optional image path; repeat for multiple images. Defaults to all four sample images.",
    )
    parser.add_argument(
        "--user-input-file",
        required=False,
        help="JSON file containing project/program inputs. Defaults to ./user_input.json.",
    )
    parser.add_argument(
        "--answers",
        help="Optional JSON file containing explicit missing user/authority facts.",
    )
    parser.add_argument(
        "--out",
        default="/tmp/vision_to_planning_design_input.json",
    )
    args = parser.parse_args()

    user_input_path = args.user_input_file or "user_input.json"
    user_input = load_user_input(user_input_path)
    _derive_tenement_carpet_areas(user_input)

    default_images = [
        Path("tests/functional/vision/data/sample1.png"),
        Path("tests/functional/vision/data/sample2.png"),
        Path("tests/functional/vision/data/sample3.png"),
        Path("tests/functional/vision/data/sample4.png"),
    ]
    image_paths = [Path(x) for x in args.images] if args.images else default_images

    print(f"[1] Processing {len(image_paths)} independent image/design cases")

    image_reports: list[dict[str, Any]] = []
    general_vision = GeneralVisionService(enable_ai=True)

    # Each image is an independent design case. Facts and regulatory
    # resolution are never merged across images.
    answers = None
    if args.answers:
        answers = json.loads(
            Path(args.answers).read_text(encoding="utf-8")
        )
        if not isinstance(answers, dict):
            raise ValueError("--answers must contain a JSON object")

    for image_path in image_paths:
        if not image_path.exists():
            raise FileNotFoundError(
                f"Vision test image not found: {image_path}"
            )

        print(f"\n--- IMAGE / DESIGN CASE: {image_path} ---")

        image_facts_for_image, evidence, mapping_info = extract_image_facts(
            image_path,
            general_vision,
        )
        extracted = image_facts_for_image.to_dict()

        # Give this image its own copy of the project/program input.
        case_user_input = json.loads(
            json.dumps(user_input, default=str)
        )
        _derive_tenement_carpet_areas(case_user_input)

        # Only this image's observations are combined with the common
        # project/program input.
        facts, conflicts, observed = build_facts(
            case_user_input,
            extracted,
        )
        observed["source_image"] = str(image_path)

        if answers:
            for field, value in answers.items():
                canonical = facts._canonical_field_name(field)

                if not hasattr(facts, canonical):
                    raise ValueError(
                        f"Unknown PlanningFacts field: {field}"
                    )

                if (
                    canonical in REGULATORY_FIELDS
                    and canonical not in {
                        "fire_approved_height_m",
                        "airport_clearance_height_m",
                    }
                ):
                    raise ValueError(
                        f"Regulatory field {canonical} must come from the "
                        "deterministic engine or authority evidence, not a "
                        "free-form answer."
                    )

                setattr(facts, canonical, value)
                facts.fact_sources[
                    canonical
                ] = "user_or_authority_answer"

            facts.normalize()

        # IMPORTANT: deterministic regulatory resolution is per image.
        resolution = resolve_until_stable(facts)

        deterministic_constraints = (
            resolution.get("final_constraints", {}) or {}
        )

        drawing_input = build_drawing_design_input(
            facts,
            resolution,
            observed,
        )

        case_report = {
            "image": str(image_path),
            "facts": extracted,
            "mapping": mapping_info,
            "vision_evidence": evidence,
            "planning_facts": facts.to_dict(),
            "deterministic_constraints": deterministic_constraints,
            "observed_drawing_design_facts": observed,
            "conflicts": conflicts,
            "resolution": resolution,
            "regulatory_status": facts.regulatory_resolution_status,
            "missing_user_inputs": facts.regulatory_user_questions,
            "required_approvals": facts.regulatory_required_approvals,
            "drawing_design_input": drawing_input,
        }

        image_reports.append(case_report)

        print(
            json.dumps(
                {
                    "image": str(image_path),
                    "deterministic_constraints": deterministic_constraints,
                    "missing_user_inputs": (
                        facts.regulatory_user_questions
                    ),
                    "required_approvals": (
                        facts.regulatory_required_approvals
                    ),
                },
                indent=2,
                default=str,
            )
        )

    # One independent report entry per image/design case.
    report = {
        "user_input": user_input,
        "design_case_count": len(image_reports),
        "design_cases": image_reports,
    }

    Path(args.out).write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n[10] Report written to {args.out}")

    # print(
    #     "\nARCHITECTURE CHECKS:\n"
    #     "  1. Image AI extracts observed site facts only.\n"
    #     "  2. Per-tenement carpet areas are derived from requested_unit_mix + requested_unit_area.\n"
    #     "  3. PostgreSQLAuthoritativeTableResolver is authoritative for regulatory values.\n"
    #     "  4. Dependent deterministic rules are re-evaluated until stable.\n"
    #     "  5. All final constraint values and rule metadata are forwarded to drawing input.\n"
    #     "  6. Missing project inputs are surfaced instead of guessed.\n"
    #     "  7. Approval/NOC metadata is surfaced from explicit DB rule results.\n"
    #     "  8. Drawing-only observed floor/height values are never silently selected as design values.\n"
    # )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
