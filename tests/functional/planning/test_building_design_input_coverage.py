from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any

from townplanning.modules.planning.domain.planning_facts import PlanningFacts
from townplanning.modules.planning.services.planning_service import PlanningService

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# =============================================================================
# PURPOSE
# =============================================================================
#
# This test intentionally treats PlanningFacts as the canonical deterministic
# planning state.
#
# AI is allowed only to extract source facts from an image. It is NOT allowed
# to calculate FSI, setbacks, parking, height, fire, lift, etc.
#
# PostgreSQL + the deterministic rule engine are authoritative for regulatory
# values. When one rule exposes a value needed by another rule, the value is
# written back into PlanningFacts and the rules are evaluated again until the
# state stops changing. If an applicable rule still requires a genuine project
# fact, the test prints a user question instead of guessing.
# =============================================================================

USER_FACTS = {
    "project_type": "Residential Apartment",
    "development_type": "New Construction",
    "zone": "Residential R-1",
    "zone_type": "Residential",
    "land_use_zone": "R-1",
    "land_use_classification": "Residential",
    "road_width": 12.0,
    "road_widths": [12.0],
    "building_use": "residential",
    "building_type": "Residential Apartment",
    "occupancy_type": "residential",
    "planning_authority": "Pune Municipal Corporation",
    "municipal_corporation": "Pune Municipal Corporation",
    "municipality": "Pune Municipal Corporation",
    "competent_authority": "Pune Municipal Corporation",
    "city": "Pune",
    "district": "Pune",
    "state": "Maharashtra",
    "congested_area": False,
    "mixed_use": False,
    "group_housing": False,
    "group_housing_building": False,
    "existing_building": False,
    "redevelopment": False,
    "requested_unit_mix": [
        {"type": "2BHK"},
        {"type": "3BHK"},
    ],
    "maximize_fsi": True,
    "maximize_parking": True,
    "maximize_usable_area": True,
    "optimize_daylight": True,
    "optimize_ventilation": True,
    "optimize_orientation": True,
}


# Image extraction schema contains source observations only.
IMAGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "plot_area": {"type": ["number", "null"]},
        "plot_width": {"type": ["number", "null"]},
        "plot_depth": {"type": ["number", "null"]},
        "plot_shape": {"type": ["string", "null"]},
        "north_direction": {"type": ["number", "null"]},
        "road_width": {"type": ["number", "null"]},
        "road_locations": {"type": "array", "items": {"type": "string"}},
        "road_frontage_count": {"type": ["integer", "null"]},
        "road_type": {"type": ["string", "null"]},
        "road_classification": {"type": ["string", "null"]},
        "access_available": {"type": ["boolean", "null"]},
        "access_width": {"type": ["number", "null"]},
        "access_length": {"type": ["number", "null"]},
        "boundary_present": {"type": ["boolean", "null"]},
        "reservation_present": {"type": ["boolean", "null"]},
        "road_widening": {"type": ["boolean", "null"]},
        "existing_building": {"type": ["boolean", "null"]},
        "building_height": {"type": ["number", "null"]},
        "number_of_floors": {"type": ["integer", "null"]},
    },
    "required": [
        "plot_area", "plot_width", "plot_depth", "plot_shape",
        "north_direction", "road_width", "road_locations",
        "road_frontage_count", "road_type", "road_classification",
        "access_available", "access_width", "access_length",
        "boundary_present", "reservation_present", "road_widening",
        "existing_building", "building_height", "number_of_floors",
    ],
}


# Fields which are regulatory state/outputs. They are never requested from the
# image model and are populated only by the deterministic engine or an actual
# authority document supplied as project input.
REGULATORY_FIELDS = PlanningFacts.regulatory_value_fields()
REGULATORY_FIELDS |= {
    "height_approval_required",
    "height_limit_basis",
    "fire_approval_status",
    "fire_approval_authority",
    "fire_approved_height_source",
}


# =============================================================================
# IMAGE FACT EXTRACTION
# =============================================================================

def _image_data_url(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    mime, _ = mimetypes.guess_type(p.name)
    mime = mime or "image/png"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode('ascii')}"


def extract_image_facts(image_path: str) -> dict[str, Any]:
    if OpenAI is None:
        raise RuntimeError("Install OpenAI SDK: pip install -U openai")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = """
Extract ONLY visibly stated site/plan facts from this drawing.

Do not calculate or infer any regulatory result.
Do not calculate FSI, setbacks, parking, height limits, fire/lift/stair rules,
coverage, storeys, or approvals.
Use a dimension only when explicitly labelled/readable.
Return null when a fact is absent or unclear.
A visible floor count or height is an OBSERVED DRAWING FACT only.
"""
    response = client.responses.create(
        model="gpt-5.6-luna",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": _image_data_url(image_path)},
            ],
        }],
        text={
            "format": {
                "type": "json_schema",
                "name": "site_plan_facts",
                "strict": True,
                "schema": IMAGE_SCHEMA,
            }
        },
    )
    return json.loads(response.output_text)


# =============================================================================
# FACT BUILDING
# =============================================================================

def _set_source_fact(
    facts: PlanningFacts,
    field: str,
    value: Any,
    source: str,
    conflicts: list[dict[str, Any]],
) -> None:
    if value is None or not hasattr(facts, field):
        return
    current = getattr(facts, field)
    if current is None or current == [] or current == {}:
        setattr(facts, field, value)
        facts.fact_sources[field] = source
        return
    if current != value:
        conflicts.append({
            "field": field,
            "existing": current,
            "incoming": value,
            "existing_source": facts.fact_sources.get(field, "unknown"),
            "incoming_source": source,
            "resolution": "existing authoritative source retained",
        })


def build_facts(image_facts: dict[str, Any] | None) -> tuple[PlanningFacts, list[dict[str, Any]], dict[str, Any]]:
    facts = PlanningFacts()
    conflicts: list[dict[str, Any]] = []
    observed: dict[str, Any] = {}

    for field, value in USER_FACTS.items():
        _set_source_fact(facts, field, value, "user", conflicts)

    for field, value in (image_facts or {}).items():
        if value is None:
            continue
        if field in {"building_height", "number_of_floors"}:
            observed[field] = value
            continue
        if field == "boundary_present":
            if value is True and facts.boundary is None:
                facts.boundary = "image_boundary_present"
                facts.fact_sources["boundary"] = "image"
            continue
        _set_source_fact(facts, field, value, "image", conflicts)

    if facts.road_width is not None:
        facts.road_widths = [float(facts.road_width)]

    facts.normalize()
    return facts, conflicts, observed


# =============================================================================
# DETERMINISTIC RULE GRAPH
# =============================================================================

def _constraint_dict(constraints: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in getattr(constraints, "__dataclass_fields__", {}):
        value = getattr(constraints, name, None)
        if value is not None:
            result[name] = value
    return result


def _apply_constraints(facts: PlanningFacts, constraints: Any) -> list[str]:
    return facts.apply_deterministic_constraints(
        constraints,
        source="postgresql_rule_engine",
    )


def _extract_missing_field(reason: str) -> str | None:
    match = re.search(r"Missing fact:\s*([A-Za-z_][A-Za-z0-9_]*)", reason or "")
    if match:
        return match.group(1)
    return None


def _condition_fields(node: Any) -> set[str]:
    """Extract explicit field operands from condition_json without inference."""
    fields: set[str] = set()
    if isinstance(node, dict):
        if isinstance(node.get("field"), str):
            fields.add(node["field"])
        for key, value in node.items():
            if key.endswith("_min") or key.endswith("_max"):
                fields.add(key.rsplit("_", 1)[0])
            elif key not in {"value", "unit", "criteria", "message"}:
                fields |= _condition_fields(value)
    elif isinstance(node, list):
        for item in node:
            fields |= _condition_fields(item)
    return fields


def _missing_inputs_from_rules(facts: PlanningFacts, constraints: Any) -> list[dict[str, Any]]:
    missing: dict[str, dict[str, Any]] = {}
    dataclass_fields = set(getattr(facts, "__dataclass_fields__", {}))

    for rule in getattr(constraints, "unresolved_rules", []) or []:
        reason = str(getattr(rule, "reason", "") or "")
        candidates = set()
        explicit = _extract_missing_field(reason)
        if explicit:
            candidates.add(explicit)
        candidates |= _condition_fields(getattr(rule, "condition", {}) or {})

        for raw in candidates:
            canonical = facts._canonical_field_name(raw)
            if canonical not in dataclass_fields:
                continue
            if canonical in REGULATORY_FIELDS:
                continue
            if facts.has(canonical):
                continue
            # Constants/placeholders in malformed DB conditions are not user
            # facts. Only actual PlanningFacts fields can reach this point.
            missing.setdefault(canonical, {
                "field": canonical,
                "reason": reason or "Required by an unresolved applicable rule.",
                "rule_id": str(getattr(rule, "rule_id", "")),
                "regulation_id": str(getattr(rule, "regulation_id", "")),
                "rule_name": getattr(rule, "name", ""),
            })
    return list(missing.values())


def _approval_requirements(constraints: Any) -> list[dict[str, Any]]:
    """Read explicit approval/NOC metadata from DB rule results.

    This function does not infer an approval from city/zone. It only surfaces
    approval information explicitly stored in a rule result/metadata/description.
    """
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    approval_keys = {
        "approval_required", "requires_approval", "required_approval",
        "noc_required", "requires_noc", "required_noc", "approval_type",
        "noc_type", "authority", "approval_authority",
    }
    explicit_text = re.compile(r"\b(?:approval|NOC|no objection certificate)\b", re.I)

    for rule in getattr(constraints, "applied_rules", []) or []:
        result = getattr(rule, "result", {}) or {}
        metadata = getattr(rule, "metadata", {}) or {}
        description = getattr(rule, "description", "") or ""
        values = {}
        if isinstance(result, dict):
            values.update(result)
        if isinstance(metadata, dict):
            values.update({f"metadata.{k}": v for k, v in metadata.items()})
        text = " ".join(str(v) for v in values.values()) + " " + str(description)

        explicit = {k: v for k, v in values.items() if k.split(".")[-1] in approval_keys}
        if not explicit and not explicit_text.search(text):
            continue

        rule_id = str(getattr(rule, "rule_id", ""))
        key = rule_id + "|" + text[:300]
        if key in seen:
            continue
        seen.add(key)
        output.append({
            "rule_id": rule_id,
            "regulation_id": str(getattr(rule, "regulation_id", "")),
            "rule_name": getattr(rule, "name", ""),
            "approval_metadata": explicit,
            "text": text[:1000],
        })
    return output


def resolve_until_stable(
    facts: PlanningFacts,
    *,
    max_passes: int = 8,
) -> dict[str, Any]:
    """Resolve DB rules repeatedly until no deterministic fact changes.

    This is the important architectural behavior: rule A may produce a value
    needed by rule B; B is evaluated again after A's value is placed in
    PlanningFacts. No regulatory value is hardcoded in this test.
    """
    service = PlanningService()
    passes: list[dict[str, Any]] = []
    all_changed: list[str] = []
    all_approvals: list[dict[str, Any]] = []
    last_constraints = None

    try:
        for pass_no in range(1, max_passes + 1):
            facts.regulatory_resolution_pass = pass_no
            constraints = service.evaluate(facts)
            last_constraints = constraints
            changed = _apply_constraints(facts, constraints)
            all_changed.extend(changed)

            approvals = _approval_requirements(constraints)
            for item in approvals:
                if item not in all_approvals:
                    all_approvals.append(item)

            passes.append({
                "pass": pass_no,
                "changed_fields": changed,
                "constraint_values": _constraint_dict(constraints),
                "applied_rule_count": len(getattr(constraints, "applied_rules", []) or []),
                "unresolved_rule_count": len(getattr(constraints, "unresolved_rules", []) or []),
                "rejected_rule_count": len(getattr(constraints, "rejected_rules", []) or []),
            })

            if not changed:
                break

        missing = _missing_inputs_from_rules(facts, last_constraints) if last_constraints else []
        for item in missing:
            facts.record_missing_input(
                item["field"],
                reason=item["reason"],
                rule_id=item["rule_id"] or None,
                regulation_id=item["regulation_id"] or None,
            )

        for approval in all_approvals:
            metadata = approval.get("approval_metadata") or {}
            approval_type = (
                metadata.get("approval_type")
                or metadata.get("metadata.approval_type")
                or metadata.get("noc_type")
                or "regulatory approval/NOC"
            )
            authority = (
                metadata.get("authority")
                or metadata.get("approval_authority")
                or metadata.get("metadata.authority")
            )
            required = metadata.get("approval_required")
            if required is None:
                required = metadata.get("requires_approval")
            if required is None:
                required = metadata.get("noc_required")
            if required is None:
                required = True
            facts.record_required_approval(
                str(approval_type),
                authority=str(authority) if authority else None,
                required=bool(required),
                available=None,
                rule_id=approval.get("rule_id") or None,
                regulation_id=approval.get("regulation_id") or None,
            )

        facts.finalize_regulatory_resolution()
        return {
            "passes": passes,
            "stable": bool(passes) and not passes[-1]["changed_fields"],
            "changed_fields": sorted(set(all_changed)),
            "missing_inputs": missing,
            "approval_requirements": all_approvals,
            "final_constraints": _constraint_dict(last_constraints) if last_constraints else {},
        }
    finally:
        close = getattr(service, "close", None)
        if callable(close):
            close()


def apply_authority_answers(facts: PlanningFacts, answers: dict[str, Any]) -> None:
    """Apply explicit user/authority answers; never calculate them."""
    for field, value in answers.items():
        canonical = facts._canonical_field_name(field)
        if not hasattr(facts, canonical):
            raise ValueError(f"Unknown PlanningFacts field: {field}")
        if canonical in REGULATORY_FIELDS and canonical not in {
            "fire_approved_height_m",
            "airport_clearance_height_m",
        }:
            raise ValueError(
                f"Regulatory field {canonical} must come from the deterministic engine or authority evidence, not a free-form answer."
            )
        setattr(facts, canonical, value)
        facts.fact_sources[canonical] = "user_or_authority_answer"
    facts.normalize()


# =============================================================================
# MAIN TEST
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic PlanningFacts -> PostgreSQL rule graph -> exact regulatory state test."
    )
    parser.add_argument("--image")
    parser.add_argument("--answers", help="JSON file containing explicit missing user/authority facts.")
    parser.add_argument("--out", default="/tmp/building_design_input_coverage_v4.json")
    args = parser.parse_args()

    image_facts = None
    if args.image:
        print(f"[1] Extracting source facts from image: {args.image}")
        image_facts = extract_image_facts(args.image)
        print(json.dumps(image_facts, indent=2))
    else:
        print("[1] No image supplied; using source/user facts only.")

    facts, conflicts, observed = build_facts(image_facts)

    print("\n[2] Initial canonical PlanningFacts")
    print(json.dumps(facts.to_dict(), indent=2, default=str))
    print("\nObserved drawing-only values:")
    print(json.dumps(observed, indent=2, default=str))

    if args.answers:
        answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        if not isinstance(answers, dict):
            raise ValueError("--answers must contain a JSON object")
        apply_authority_answers(facts, answers)
        print("\n[3] Explicit user/authority answers applied")
        print(json.dumps(answers, indent=2, default=str))
    else:
        print("\n[3] No additional answers supplied.")

    print("\n[4] Deterministic PostgreSQL rule graph resolution")
    resolution = resolve_until_stable(facts)
    print(json.dumps(resolution, indent=2, default=str))

    print("\n[5] FINAL DETERMINISTIC PLANNING FACTS")
    print(json.dumps(facts.to_dict(), indent=2, default=str))

    print("\n[6] USER INPUTS STILL REQUIRED")
    if facts.regulatory_user_questions:
        for q in facts.regulatory_user_questions:
            print(json.dumps(q, ensure_ascii=False))
    else:
        print("None")

    print("\n[7] APPROVALS / NOCs")
    if facts.regulatory_required_approvals:
        print(json.dumps(facts.regulatory_required_approvals, indent=2, default=str))
    else:
        print("None explicitly surfaced by DB rule results.")

    report = {
        "user_input": USER_FACTS,
        "image_facts": image_facts,
        "observed_drawing_design_facts": observed,
        "canonical_planning_facts": facts.to_dict(),
        "conflicts": conflicts,
        "resolution": resolution,
        "regulatory_status": facts.regulatory_resolution_status,
        "missing_user_inputs": facts.regulatory_user_questions,
        "required_approvals": facts.regulatory_required_approvals,
    }
    Path(args.out).write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n[8] Report written to {args.out}")

    print(
        "\nARCHITECTURE CHECKS:\n"
        "  1. Image AI extracts facts only.\n"
        "  2. PostgreSQL is authoritative for regulatory values.\n"
        "  3. Deterministic constraints are copied into PlanningFacts.\n"
        "  4. Dependent rules are re-evaluated until the state is stable.\n"
        "  5. No regulation-specific numeric threshold is hardcoded in this test.\n"
        "  6. Genuine missing project inputs are returned as user questions.\n"
        "  7. Approval/NOC requirements are surfaced from explicit DB rule metadata/text.\n"
        "  8. Observed drawing floors/height are never silently selected as design values."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
