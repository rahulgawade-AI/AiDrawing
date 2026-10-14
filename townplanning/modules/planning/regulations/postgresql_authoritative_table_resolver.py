from __future__ import annotations

import re
import json
import os
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from townplanning.modules.planning.domain.regulatory_input_requirements import (
    FIELD_INPUT_REQUIREMENTS,
    validate_required_inputs,
)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from townplanning.infrastructure.database.models import Table as TableModel


# ============================================================================
# Result models
# ============================================================================
CONSTRAINT_SPECS = {
    # ========================================================================
    # CONSTRAINT GROUP 1: FSI
    #
    # UDCPR source:
    #   Regulation 6.3 -> Table 6-G
    #
    # This resolver intentionally handles ONLY FSI in this version.
    # Setbacks, parking, height, fire, open-space, etc. will be added later
    # one constraint family at a time.
    #
    # IMPORTANT:
    #   No regulatory numeric value is hard-coded here.
    #   The value is always read from the PostgreSQL TableModel after the
    #   applicable row/column has been selected deterministically.
    # ========================================================================

    "basic_fsi": {
        "kind": "table",
        "table_numbers": {"6-G"},
        "column_aliases": (
            "basic fsi",
        ),
        "dimensions": (
            "road_width",
            "planning_authority",
            "zone_type",
            "land_use_zone",
        ),
    },

    "premium_fsi": {
        "kind": "table",
        "table_numbers": {"6-G"},
        "column_aliases": (
            "fsi on payment of premium",
            "premium fsi",
        ),
        "dimensions": (
            "road_width",
            "planning_authority",
            "zone_type",
            "land_use_zone",
        ),
    },

    "tdr_fsi": {
        "kind": "table",
        "table_numbers": {"6-G"},
        "column_aliases": (
            "maximum permissible tdr loading",
            "maximum permissible tdr",
            "tdr loading",
            "tdr fsi",
        ),
        "dimensions": (
            "road_width",
            "planning_authority",
            "zone_type",
            "land_use_zone",
        ),
    },

    "maximum_fsi": {
        "kind": "table",
        "table_numbers": {"6-G"},
        "column_aliases": (
            "maximum building potential on plot including in-situ fsi",
            "maximum building potential on plot including insitu fsi",
            "maximum building potential on plot",
            "maximum building potential",
            "maximum permissible fsi",
        ),
        "dimensions": (
            "road_width",
            "planning_authority",
            "zone_type",
            "land_use_zone",
        ),
    },

    # ========================================================================
    # CONSTRAINT GROUP 2: SETBACKS / MARGINS
    # UDCPR 6.2.1 -> Table 6-D
    # ========================================================================
    "front_setback": {
        "kind": "table",
        "table_numbers": {"6-D"},
        "column_aliases": (
            "minimum setback from road side in meters",
            "min setback from road side in meters",
            "front setback",
        ),
        "dimensions": ("road_width",),
    },
    "rear_setback": {
        "kind": "table",
        "table_numbers": {"6-D"},
        "column_aliases": (
            "minimum rear margins in meters",
            "min rear margins in meters",
            "rear setback",
            "rear margin",
        ),
        "dimensions": ("road_width",),
    },
    "side_setback_left": {
        "kind": "table",
        "table_numbers": {"6-D"},
        "column_aliases": (
            "minimum side margins in meters",
            "min side margins in meters",
            "side margins",
            "side setback",
        ),
        "dimensions": ("road_width",),
    },
    "side_setback_right": {
        "kind": "table",
        "table_numbers": {"6-D"},
        "column_aliases": (
            "minimum side margins in meters",
            "min side margins in meters",
            "side margins",
            "side setback",
        ),
        "dimensions": ("road_width",),
    },
    "car_parking_required": {
        "kind": "table",
        "table_numbers": {"8-B"},
        "column_aliases": ("car", "cars", "car parking", "parking spaces required car"),
        "dimensions": ("tenement_carpet_areas", "land_use", "occupancy"),
    },
    "two_wheeler_parking_required": {
        "kind": "table",
        "table_numbers": {"8-B"},
        "column_aliases": ("scooter", "scooters", "two wheeler", "two wheeler parking"),
        "dimensions": ("tenement_carpet_areas", "land_use", "occupancy"),
    },
    "visitor_parking_required": {
        "kind": "table",
        "table_numbers": {"8-B"},
        "column_aliases": ("visitor parking", "visitor", "visitors"),
        "dimensions": ("tenement_carpet_areas", "land_use", "occupancy"),
    },
    "parking_factor": {
        "kind": "table",
        "table_numbers": {"8-C"},
        "column_aliases": ("multiplying factor", "parking factor"),
        "dimensions": ("planning_authority", "municipality", "competent_authority"),
    },
}
# ============================================================================
# Required PlanningFacts inputs
# ============================================================================
#
# These are the minimum inputs needed before attempting to resolve each
# constraint family.
#
# IMPORTANT:
# - Do NOT blindly use CONSTRAINT_SPECS["dimensions"] here.
# - Some table dimensions are optional branches and are only required when
#   the selected regulatory evidence actually distinguishes them.
# - Missing inputs are reported explicitly instead of allowing OpenAI to guess.
# ============================================================================

@dataclass(slots=True)
class SelectedTable:
    regulation_number: str
    table_number: str
    table_title: str
    table: Any = None
    reason: str = ""
    source_text: str = ""


@dataclass(slots=True)
class PostgreSQLConstraint:
    key: str
    value: Any
    unit: str | None
    source_rule_id: str
    regulation_id: str
    rule_name: str
    category: str
    priority: int
    status: str = "verified"
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PostgreSQLResolution:
    constraints: list[PostgreSQLConstraint] = field(
        default_factory=list
    )
    warnings: list[str] = field(
        default_factory=list
    )
    errors: list[str] = field(
        default_factory=list
    )
    missing_inputs: list[str] = field(
        default_factory=list
    )
    selections: list[SelectedTable] = field(
        default_factory=list
    )
    # Regulatory paragraph/source evidence selected by Chroma.  This is kept
    # separately because a constraint can be stated in prose rather than a
    # table, and OpenAI must receive that evidence as well.
    paragraph_sources: list[dict[str, Any]] = field(
        default_factory=list
    )
    status: str = "INSUFFICIENT_RULE_DATA"


# ============================================================================
# Resolver
# ============================================================================


class PostgreSQLAuthoritativeTableResolver:

    # ------------------------------------------------------------------
    # Semantic aliases.
    #
    # These are ONLY column/header names.
    # Regulatory values are never stored here.
    # ------------------------------------------------------------------

    FIELD_ALIASES = {
        "basic_fsi": (
            "basic fsi",
            "basic floor space index",
        ),
        "premium_fsi": (
            "premium fsi",
            "fsi on payment of premium",
            "fsi on premium",
        ),
        "tdr_fsi": (
            "tdr fsi",
            "tdr loading",
            "maximum permissible tdr loading",
            "tdr",
        ),
        "maximum_fsi": (
            "maximum fsi",
            "maximum permissible fsi",
            "maximum building potential",
            "maximum building potential on plot",
            "maximum building potential on plot including in-situ fsi",
            "building potential",
        ),
        "front_setback": ("front setback", "minimum setback from road side", "min setback from road side"),
        "rear_setback": ("rear setback", "rear margin", "minimum rear margins"),
        "side_setback_left": ("side setback", "side margins", "minimum side margins"),
        "side_setback_right": ("side setback", "side margins", "minimum side margins"),
        "car_parking_required": ("car", "cars", "car parking"),
        "two_wheeler_parking_required": ("scooter", "scooters", "two wheeler", "two wheeler parking"),
        "visitor_parking_required": ("visitor parking", "visitor", "visitors"),
        "parking_factor": ("multiplying factor", "parking factor"),
    }

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def __init__(self, session):
        self.session = session

    # =========================================================================
    # Public API
    # =========================================================================

    def resolve(
        self,
        facts,
        selected_regulations: list[Any] | None = None,
        chroma_sources: list[Any] | None = None,
        requested_fields: list[str] | None = None,
        regulatory_sources: list[Any] | None = None,
    ) -> PostgreSQLResolution:
        """Resolve selected regulatory evidence without inventing values.

        Source precedence is deliberate:
          1. Chroma-selected table payload, when the payload actually contains
             table data.
          2. Otherwise the matching PostgreSQL TableModel.
          3. Paragraph/source text is always retained and sent to the final
             OpenAI evidence extractor.

        OpenAI is never allowed to discover an unrelated regulation/table.
        It only extracts requested fields from the evidence selected here.
        """
        if chroma_sources is None:
            chroma_sources = regulatory_sources

        selected_regulations = [str(x).strip() for x in (selected_regulations or []) if str(x).strip()]
        requested_fields = list(dict.fromkeys(requested_fields or []))
        sources = list(chroma_sources or [])
        result = PostgreSQLResolution()

        if not selected_regulations:
            result.status = "INSUFFICIENT_RULE_DATA"
            result.warnings.append("No selected regulations were supplied.")
            return result

        processed_tables: set[tuple[str, str]] = set()

        for number in selected_regulations:
            matching_sources = self._sources_for_regulation(number, sources)
            source_text = "\n".join(
                str(self._source_text_from_source(src)).strip()
                for src in matching_sources
                if str(self._source_text_from_source(src)).strip()
            )

            # Preserve prose even when no table is referenced.
            for src in matching_sources:
                text = str(self._source_text_from_source(src)).strip()
                if not text:
                    continue
                paragraph = {
                    "regulation_number": number,
                    "source_type": "paragraph",
                    "text": text,
                }
                if paragraph not in result.paragraph_sources:
                    result.paragraph_sources.append(paragraph)

            # Prefer an explicit Chroma table_number.  Only fall back to
            # parsing source text when the metadata did not carry one.
            table_numbers = self._explicit_table_numbers_from_sources(matching_sources)
            if not table_numbers:
                table_numbers = self._extract_table_references([source_text])

            if not table_numbers:
                # This is not an error: the selected evidence may be a prose
                # rule.  OpenAI will extract paragraph-backed constraints.
                if source_text:
                    continue
                result.warnings.append(
                    f"No table or paragraph evidence found for regulation {number}."
                )
                continue

            for raw_table_number in table_numbers:
                table_number = self._clean_table_number(raw_table_number)
                if not table_number:
                    continue
                key = (number, table_number)
                if key in processed_tables:
                    continue
                processed_tables.add(key)

                # If Chroma contains the complete table, use that exact table
                # payload.  Otherwise PostgreSQL remains the authoritative
                # fallback.
                table = self._chroma_table_for_sources(matching_sources, table_number)
                source_name = "chroma" if table is not None else "postgresql"
                if table is None:
                    table = self._find_postgresql_table(number, table_number)

                if table is None:
                    result.warnings.append(
                        f"Neither Chroma nor PostgreSQL table {table_number} "
                        f"selected for regulation {number} was found."
                    )
                    continue

                title = self._table_title(table, table_number)
                selection = SelectedTable(
                    regulation_number=number,
                    table_number=table_number,
                    table_title=title,
                    table=table,
                    reason=(
                        "Table selected from Chroma table payload."
                        if source_name == "chroma"
                        else "Table selected from regulatory source evidence and loaded from PostgreSQL."
                    ),
                    source_text=source_text,
                )
                result.selections.append(selection)

                # Keep the existing deterministic parser as a diagnostic/
                # fallback artifact, but final returned values come only from
                # OpenAI over the selected evidence.
                try:
                    table_json = self._table_to_json(table)
                    extracted = self._extract_from_table_json(
                        table_json=table_json,
                        facts=facts,
                        requested_fields=requested_fields,
                        regulation_number=number,
                        table_number=table_number,
                    )
                    # Deliberately not merged into final constraints.
                    _ = extracted
                except Exception as exc:
                    result.warnings.append(
                        f"Deterministic diagnostic extraction failed for {number}/{table_number}: {exc}"
                    )

                # Follow explicit table-to-table references, but only within
                # the selected regulation evidence.
                try:
                    referenced_tables = self._extract_table_references_from_table(
                        self._table_to_json(table)
                    )
                except Exception:
                    referenced_tables = []

                for referenced in referenced_tables:
                    ref_key = (number, self._clean_table_number(referenced))
                    if ref_key in processed_tables:
                        continue
                    processed_tables.add(ref_key)

                    ref_table = self._chroma_table_for_sources(matching_sources, referenced)
                    ref_source_name = "chroma" if ref_table is not None else "postgresql"
                    if ref_table is None:
                        ref_table = self._find_postgresql_table(number, referenced)
                    if ref_table is None:
                        continue

                    result.selections.append(
                        SelectedTable(
                            regulation_number=number,
                            table_number=self._clean_table_number(referenced),
                            table_title=self._table_title(ref_table, referenced),
                            table=ref_table,
                            reason=(
                                f"Referenced by selected Table {table_number}; source={ref_source_name}."
                            ),
                            source_text=source_text,
                        )
                    )
        # ---------------------------------------------------------------
        # Deterministic input validation
        # ---------------------------------------------------------------
        blocked_fields = self._validate_required_inputs(
            facts=facts,
            requested_fields=requested_fields,
            result=result,
        )

        # Only send fields with the required application inputs to OpenAI.
        # Fields blocked by missing inputs remain unresolved and are reported
        # through result.missing_inputs.
        extractable_fields = [
            field
            for field in requested_fields
            if field not in blocked_fields
        ]

        ai_constraints = self._extract_selected_tables_with_openai(
            facts=facts,
            selections=result.selections,
            paragraph_sources=result.paragraph_sources,
            requested_fields=extractable_fields,
        )
        result.constraints = self._deduplicate_constraints(ai_constraints, result)

        # for field in getattr(self, "_last_openai_missing_fields", []):
        #     result.warnings.append(
        #         f"OpenAI could not establish requested constraint '{field}' from selected regulatory evidence."
        #     )
        for field, missing in blocked_fields.items():
            result.warnings.append(
                f"Missing required input(s) for '{field}': "
                + ", ".join(missing)
            )

        if result.errors:
            result.status = "ERROR"
        elif result.constraints:
            result.status = "PARTIAL" if (result.warnings or result.missing_inputs) else "RESOLVED"
        else:
            result.status = "INSUFFICIENT_RULE_DATA"
        return result


    def _validate_required_inputs(
    self,
    facts,
    requested_fields,
    result,
):
        """
        Determine which requested PlanningFacts constraints cannot be resolved
        because required application inputs are missing.

        This is deterministic. OpenAI is not involved.

        Returns:
            dict[field, list[str]]:
                Fields that are blocked by missing inputs.
        """

        blocked, missing_inputs = validate_required_inputs(
            facts, requested_fields
        )
        result.missing_inputs.extend(missing_inputs)
        return blocked

    def _extract_selected_tables_with_openai(
        self,
        *,
        facts: Any,
        selections: list[SelectedTable],
        paragraph_sources: list[dict[str, Any]] | None = None,
        requested_fields: list[str],
    ) -> list[PostgreSQLConstraint]:
        """Extract requested regulatory values from already-selected tables.

        Important boundary:
          1. Python/Chroma selects the regulation/table.
          2. PostgreSQL supplies the complete selected table.
          3. OpenAI only reads those supplied tables and maps exact table
             values to requested fields.
          4. OpenAI is forbidden from using outside knowledge, inventing
             values, or selecting another table.

        This deliberately supports tables whose semantic headers are embedded
        in the table rows rather than in TableModel.headers.
        """
        if not requested_fields:
            return []
        if not selections and not paragraph_sources:
            self._last_openai_missing_fields = list(dict.fromkeys(requested_fields))
            return []

        if OpenAI is None:
            raise RuntimeError(
                "The openai package is required for selected-table extraction."
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        client = OpenAI(api_key=api_key)

        fact_payload = self._plain_value(facts)
        table_payload = []
        allowed_by_field = {}

        for selection in selections:
            table_number = str(selection.table_number).strip().upper()
            regulation_number = str(selection.regulation_number).strip()
            table = selection.table

            table_json = self._table_to_json(table)
            raw_headers = getattr(table, "headers", None)
            raw_rows = getattr(table, "rows", None)
            markdown = getattr(table, "markdown", None)

            table_payload.append({
                "regulation_number": regulation_number,
                "table_number": table_number,
                "table_title": selection.table_title,
                "table_source": (
                    "chroma"
                    if str(selection.reason).lower().find("chroma") >= 0
                    else "postgresql"
                ),
                "source_text": selection.source_text,
                "headers": raw_headers,
                "rows": raw_rows,
                "markdown": markdown,
                "normalized_json": table_json,
            })

        for field in requested_fields:
            spec = CONSTRAINT_SPECS.get(field, {})
            allowed = {
                str(x).strip().upper()
                for x in spec.get("table_numbers", set())
            }
            allowed_by_field[field] = sorted(allowed)

        system_prompt = r"""
You are the FINAL REGULATORY CONSTRAINT VALUE EXTRACTOR for a UDCPR planning application.

The application has ALREADY selected the relevant regulatory evidence. Extract requested values ONLY from the supplied evidence. Evidence may contain PostgreSQL tables AND regulatory paragraph/source text.

RULES:
1. Use only supplied evidence. Never use outside UDCPR knowledge.
2. Do not select a different regulation or table.
3. A value may come from an explicit paragraph/source-text statement even when it is not in a table.
4. If paragraph text explicitly refers to a supplied table, use that table.
5. If a selected table references another supplied table, follow that evidence chain.
6. Inspect PostgreSQL headers, embedded header rows, raw rows, markdown and normalized_json together.
7. Match PlanningFacts to the applicable row/condition.
8. Never invent, estimate, interpolate or substitute regulatory values.
9. Deterministic arithmetic is allowed only when the supplied rule explicitly requires it and all operands are supplied.
10. Do not round unless the supplied rule explicitly requires rounding.
11. Return exactly one object for every requested field. If evidence is insufficient, return null.
12. Every non-null result must identify the exact regulation_number and source_type.
13. For source_type=table, table_number must identify a supplied selected table. For source_type=paragraph, table_number must be null.
14. The allowed_table_by_field mapping is a provenance validation boundary.
15. Prefer direct evidence over inference.
16. Return JSON only.
"""

        paragraph_sources = list(paragraph_sources or [])
        seen = {(str(p.get("regulation_number", "")).strip(), str(p.get("text", "")).strip()) for p in paragraph_sources}
        for selection in selections:
            text = str(selection.source_text or "").strip()
            if not text:
                continue
            key = (str(selection.regulation_number).strip(), text)
            if key in seen:
                continue
            seen.add(key)
            paragraph_sources.append({
                "regulation_number": str(selection.regulation_number).strip(),
                "source_type": "paragraph",
                "text": text,
            })

        user_payload = {
            "planning_facts": fact_payload,
            "requested_fields": requested_fields,
            "allowed_table_by_field": allowed_by_field,
            "selected_postgresql_tables": table_payload,
            "selected_regulatory_paragraph_sources": paragraph_sources,
        }

        response = client.responses.create(
            model=model,
            instructions=system_prompt,
            input=json.dumps(user_payload, ensure_ascii=False, default=str),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "selected_table_regulatory_values",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "constraints": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "field": {"type": "string"},
                                        "value": {
                                            "type": ["number", "string", "null"]
                                        },
                                        "unit": {
                                            "type": ["string", "null"]
                                        },
                                        "regulation_number": {"type": "string"},
                                        "table_number": {"type": ["string", "null"]},
                                        "source_type": {"type": "string"},
                                        "source_text": {"type": ["string", "null"]},
                                    },
                                    "required": [
                                        "field", "value", "unit",
                                        "regulation_number", "table_number", "source_type",
                                        "source_text",
                                    ],
                                },
                            }
                        },
                        "required": ["constraints"],
                    },
                },
                "verbosity": "low",
            },
            max_output_tokens=7000,
        )

        raw = response.output_text
        if not raw:
            raise RuntimeError("OpenAI returned an empty selected-table extraction response.")

        # print("\n" + "=" * 100)
        # print("OPENAI SELECTED-TABLE REGULATORY EXTRACTION")
        # print("=" * 100)
        # print(raw)
        # print("=" * 100)

        data = json.loads(raw)
        selected_lookup = {
            (str(s.regulation_number).strip(), str(s.table_number).strip().upper()): s
            for s in selections
        }
        selected_regulations = {str(s.regulation_number).strip() for s in selections}
        selected_regulations.update(
            str(p.get("regulation_number", "")).strip()
            for p in (paragraph_sources or [])
            if str(p.get("regulation_number", "")).strip()
        )
        requested = list(dict.fromkeys(requested_fields))
        constraints = []
        returned = set()

        for item in data.get("constraints", []):
            field = str(item.get("field", "")).strip()
            if field not in requested or field in returned:
                continue
            value = item.get("value")
            if value is None:
                continue
            regulation_number = str(item.get("regulation_number", "")).strip()
            if regulation_number not in selected_regulations:
                continue
            source_type = str(item.get("source_type", "table")).strip().lower()
            raw_table = item.get("table_number")
            table_number = str(raw_table).strip().upper() if raw_table is not None else ""

            if source_type == "table":
                selection = selected_lookup.get((regulation_number, table_number))
                if selection is None:
                    continue
                allowed = allowed_by_field.get(field, [])
                if allowed and table_number not in allowed:
                    continue
                source_rule_id = f"openai-selected-table:{regulation_number}:{table_number}"
                rule_name = selection.table_title or table_number
                source_name = (
                    "chroma"
                    if str(selection.reason).lower().find("chroma") >= 0
                    else "postgresql"
                )
                category = (
                    "chroma_selected_table"
                    if source_name == "chroma"
                    else "postgresql_authoritative_table"
                )
            elif source_type == "paragraph":
                source_rule_id = f"openai-selected-paragraph:{regulation_number}"
                rule_name = f"Regulation {regulation_number} paragraph/source"
                category = "regulatory_source_text"
                source_name = "regulatory_source"
            else:
                continue

            constraints.append(PostgreSQLConstraint(
                key=field,
                value=value,
                unit=item.get("unit"),
                source_rule_id=source_rule_id,
                regulation_id=regulation_number,
                rule_name=rule_name,
                category=category,
                priority=1,
                status="verified",
                reason=f"Value extracted by OpenAI from selected regulatory {source_type} evidence.",
                metadata={
                    "source": source_name,
                    "extraction": "openai_selected_evidence",
                    "source_type": source_type,
                    "regulation_number": regulation_number,
                    "table_number": table_number or None,
                    "source_text": item.get("source_text"),
                },
            ))
            returned.add(field)

        self._last_openai_missing_fields = [f for f in requested if f not in returned]
        return constraints

    @staticmethod
    def _plain_value(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): PostgreSQLAuthoritativeTableResolver._plain_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [PostgreSQLAuthoritativeTableResolver._plain_value(v) for v in value]
        if hasattr(value, "model_dump"):
            try:
                return PostgreSQLAuthoritativeTableResolver._plain_value(value.model_dump())
            except Exception:
                pass
        if hasattr(value, "__dict__"):
            return PostgreSQLAuthoritativeTableResolver._plain_value(vars(value))
        return str(value)

    # =========================================================================
    # Source handling
    # =========================================================================

    @staticmethod
    def _source_text_from_source(source: Any) -> str:
        """Return source prose from all common Chroma/adapter field names."""
        if isinstance(source, dict):
            for key in (
                "source_text", "text", "document", "content", "page_content",
                "description", "paragraph",
            ):
                value = source.get(key)
                if value:
                    return str(value)
            return ""
        for key in (
            "source_text", "text", "document", "content", "page_content",
            "description", "paragraph",
        ):
            value = getattr(source, key, None)
            if value:
                return str(value)
        return ""

    def _sources_for_regulation(self, regulation_number: str, sources: list[Any]) -> list[Any]:
        target = self._norm(regulation_number)
        matched = []
        for source in sources:
            if isinstance(source, dict):
                source_number = (
                    source.get("regulation_number") or source.get("number") or
                    source.get("regulation") or source.get("regulation_id")
                )
            else:
                source_number = (
                    getattr(source, "regulation_number", None) or
                    getattr(source, "number", None) or
                    getattr(source, "regulation", None) or
                    getattr(source, "regulation_id", None)
                )
            text = self._source_text_from_source(source)
            if source_number is not None and self._norm(source_number) == target:
                matched.append(source)
            elif source_number is None and target in self._norm(text):
                matched.append(source)
        return matched

    @staticmethod
    def _source_field(source: Any, *names: str) -> Any:
        if isinstance(source, dict):
            for name in names:
                if source.get(name) is not None:
                    return source.get(name)
        else:
            for name in names:
                value = getattr(source, name, None)
                if value is not None:
                    return value
        return None

    def _explicit_table_numbers_from_sources(self, sources: list[Any]) -> list[str]:
        values = []
        for source in sources:
            raw = self._source_field(source, "table_number", "table_no", "table", "selected_table")
            if isinstance(raw, dict):
                raw = raw.get("table_number") or raw.get("number") or raw.get("name")
            if raw is not None and not isinstance(raw, (list, tuple, set)):
                refs = self._extract_table_references([str(raw)])
                if refs:
                    values.extend(refs)
                elif re.fullmatch(r"\d+(?:\.[0-9]+)?-[A-Za-z0-9]+", str(raw).strip()):
                    values.append(str(raw).strip())
        out = []
        for value in values:
            cleaned = self._clean_table_number(value)
            if cleaned and cleaned not in out:
                out.append(cleaned)
        return out

    def _chroma_table_for_sources(self, sources: list[Any], table_number: str) -> Any | None:
        target = self._clean_table_number(table_number)
        for source in sources:
            raw = self._source_field(source, "table_data", "table_payload", "table_content", "table")
            explicit = self._source_field(source, "table_number", "table_no", "selected_table")
            if isinstance(raw, dict):
                raw_number = raw.get("table_number") or raw.get("number") or raw.get("name")
                if raw_number and self._clean_table_number(str(raw_number)) != target:
                    continue
                if any(k in raw for k in ("headers", "rows", "markdown")):
                    return self._table_like_object(raw, target)
            elif raw is not None and explicit is not None and self._clean_table_number(str(explicit)) == target:
                if hasattr(raw, "headers") or hasattr(raw, "rows"):
                    return raw
            # Some adapters put headers/rows directly on the source.
            headers = self._source_field(source, "headers")
            rows = self._source_field(source, "rows")
            if explicit is not None and self._clean_table_number(str(explicit)) == target and (headers is not None or rows is not None):
                return self._table_like_object({
                    "headers": headers or [],
                    "rows": rows or [],
                    "markdown": self._source_field(source, "markdown") or "",
                    "title": self._source_field(source, "table_title", "title") or f"Table {target}",
                    "page": self._source_field(source, "page", "page_number"),
                    "index": self._source_field(source, "index", "table_index"),
                }, target)
        return None

    @staticmethod
    def _table_like_object(data: dict[str, Any], table_number: str) -> Any:
        class ChromaTable:
            pass
        obj = ChromaTable()
        obj.id = data.get("id") or f"chroma:{table_number}"
        obj.page = data.get("page") or data.get("page_number")
        obj.index = data.get("index") or data.get("table_index")
        obj.title = data.get("title") or data.get("table_title") or f"Table {table_number}"
        obj.headers = data.get("headers") or []
        obj.rows = data.get("rows") or []
        obj.markdown = data.get("markdown") or ""
        obj.metadata = data.get("metadata") or {}
        return obj

    def _source_text_for_regulation(
        self,
        regulation_number,
        sources,
    ):
        return "\n".join(
            text for text in (
                self._source_text_from_source(source)
                for source in self._sources_for_regulation(str(regulation_number), sources)
            )
            if str(text).strip()
        )

    # =========================================================================
    # Table reference detection
    # =========================================================================

    @classmethod
    def _extract_table_references(
        cls,
        texts,
    ):
        references = []

        pattern = re.compile(
            r"\bTable\s+"
            r"(?:No\.?\s*)?"
            r"([0-9]+"
            r"(?:\.[0-9]+)?"
            r"(?:\s*[-–]\s*[A-Za-z0-9]+))"
            r"(?=\s|[.,;:)]+|$)",
            re.I,
        )

        for text in texts:

            if not text:
                continue

            for match in pattern.finditer(
                str(text)
            ):

                value = (
                    match.group(1)
                    .strip()
                    .upper()
                    .replace("–", "-")
                )

                value = re.sub(
                    r"\s*-\s*",
                    "-",
                    value,
                )

                if value not in references:
                    references.append(
                        value
                    )

        return references

    def _extract_table_references_from_table(
        self,
        table_json,
    ):
        texts = [
            table_json.get(
                "title",
                ""
            ),
            table_json.get(
                "markdown",
                ""
            ),
        ]

        for header in (
            table_json.get(
                "headers",
                []
            )
        ):
            texts.append(
                str(header)
            )

        for row in (
            table_json.get(
                "rows",
                []
            )
        ):
            if isinstance(row, dict):
                texts.extend(
                    str(v)
                    for v in row.values()
                    if v is not None
                )
            else:
                texts.append(
                    str(row)
                )

        return self._extract_table_references(
            texts
        )

    @staticmethod
    def _clean_table_number(value):
        value = str(
            value or ""
        ).strip().upper()

        value = value.replace(
            "–",
            "-"
        )

        value = re.sub(
            r"\s*-\s*",
            "-",
            value,
        )

        return value

    # =========================================================================
    # PostgreSQL table lookup
    # =========================================================================

    def _find_postgresql_table(
        self,
        regulation_number,
        table_number,
    ):
        """
        The database's TableModel.regulation_id does not reliably point
        to the canonical RegulationModel UUID in the current database.

        Therefore table lookup deliberately uses the actual table
        content/title/markdown as the authoritative table identifier.
        """

        target = self._clean_table_number(
            table_number
        )

        stmt = (
            select(TableModel)
            .order_by(
                TableModel.page_number,
                TableModel.table_index,
            )
        )

        tables = list(
            self.session.scalars(stmt)
        )

        exact_candidates = []
        content_candidates = []

        for table in tables:

            title = str(
                getattr(
                    table,
                    "title",
                    ""
                )
                or ""
            )

            markdown = str(
                getattr(
                    table,
                    "markdown",
                    ""
                )
                or ""
            )

            headers = getattr(
                table,
                "headers",
                None,
            ) or []

            rows = getattr(
                table,
                "rows",
                None,
            ) or []

            header_text = " ".join(
                str(h)
                for h in headers
            )

            row_text = " ".join(
                str(v)
                for row in rows
                for v in (
                    row.values()
                    if isinstance(
                        row,
                        dict
                    )
                    else row
                )
                if v is not None
            )

            full_text = " ".join(
                [
                    title,
                    markdown,
                    header_text,
                    row_text,
                ]
            )

            extracted_numbers = (
                self._extract_table_references(
                    [full_text]
                )
            )

            if target in extracted_numbers:
                content_candidates.append(
                    table
                )

            # Some extractor versions put the table number directly
            # in title/metadata.
            table_title_number = (
                self._table_number(
                    full_text
                )
            )

            if (
                table_title_number
                == target
            ):
                exact_candidates.append(
                    table
                )

        if exact_candidates:
            return self._best_table_candidate(
                exact_candidates,
                target,
            )

        if content_candidates:
            return self._best_table_candidate(
                content_candidates,
                target,
            )

        return None

    @staticmethod
    def _best_table_candidate(
        candidates,
        target,
    ):
        """
        Prefer tables containing an actual structured table rather than
        a text-only false match.
        """

        def score(table):

            rows = getattr(
                table,
                "rows",
                None,
            ) or []

            headers = getattr(
                table,
                "headers",
                None,
            ) or []

            markdown = str(
                getattr(
                    table,
                    "markdown",
                    ""
                )
                or ""
            )

            return (
                len(rows) > 0,
                len(headers),
                len(markdown),
            )

        return sorted(
            candidates,
            key=score,
            reverse=True,
        )[0]

    @staticmethod
    def _table_number(text):
        if not text:
            return None

        patterns = (
            r"\btable\s*(?:no\.?\s*)?"
            r"([0-9]+\s*[-–]\s*[A-Za-z0-9]+)\b",

            r"\btable\s*(?:no\.?\s*)?"
            r"([0-9]+\s*[A-Za-z])\b",
        )

        for pattern in patterns:

            match = re.search(
                pattern,
                str(text),
                re.I,
            )

            if match:

                value = (
                    match.group(1)
                    .upper()
                    .replace(
                        "–",
                        "-"
                    )
                )

                value = re.sub(
                    r"\s*-\s*",
                    "-",
                    value,
                )

                return value

        return None

    @staticmethod
    def _table_title(
        table,
        table_number,
    ):
        title = str(
            getattr(
                table,
                "title",
                ""
            )
            or ""
        ).strip()

        if title:
            return title

        return f"Table {table_number}"

    # =========================================================================
    # PostgreSQL table -> normalized JSON
    # =========================================================================





    def _row_values(self, row):
        """
        Convert a PostgreSQL table row into values ordered by column position.

        Supports:
        - list / tuple rows
        - normalized JSON dictionaries
        - C[n] dictionary keys
        - numeric dictionary keys
        """

        if row is None:
            return []

        # Already an ordered row.
        if isinstance(row, (list, tuple)):
            return list(row)

        if not isinstance(row, dict):
            return [row]

        # ------------------------------------------------------------
        # PostgreSQL / extracted-table rows may use:
        #
        #   C[0], C[1], C[2] ...
        # or
        #   0, 1, 2 ...
        #
        # Sort these by their numeric column position.
        # ------------------------------------------------------------
        indexed = []

        for key, value in row.items():

            key_text = str(key).strip()

            match = re.fullmatch(
                r"C\[\s*(\d+)\s*\]",
                key_text,
                re.IGNORECASE,
            )

            if match:
                indexed.append(
                    (int(match.group(1)), value)
                )
                continue

            if key_text.isdigit():
                indexed.append(
                    (int(key_text), value)
                )
                continue

        if indexed:
            indexed.sort(key=lambda item: item[0])
            return [value for _, value in indexed]

        # ------------------------------------------------------------
        # Already-normalized semantic dictionary.
        #
        # Preserve insertion order.
        # ------------------------------------------------------------
        return list(row.values())


    def _table_to_json(
    self,
    table,
):
        """
        Convert the complete PostgreSQL TableModel into a stable,
        header-aware JSON representation.

        PostgreSQL/PDF extraction may store rows as:
            1. dictionaries keyed by actual header text
            2. dictionaries keyed by numeric column indexes
            3. lists/tuples
            4. dictionaries with C0/C1/C2 style keys

        The resolver must normalize all of those forms into:

            {
                "Header 1": value,
                "Header 2": value,
                ...
            }

        Regulatory values are never generated here.
        """

        headers = (
            getattr(
                table,
                "headers",
                None,
            )
            or []
        )

        rows = (
            getattr(
                table,
                "rows",
                None,
            )
            or []
        )

        title = str(
            getattr(
                table,
                "title",
                "",
            )
            or ""
        )

        markdown = str(
            getattr(
                table,
                "markdown",
                "",
            )
            or ""
        )

        # --------------------------------------------------------------
        # Normalize headers.
        # --------------------------------------------------------------

        normalized_headers = (
            self._normalize_headers(
                headers
            )
        )

        # --------------------------------------------------------------
        # If headers are unavailable, try extracting them from markdown.
        # --------------------------------------------------------------

        if not normalized_headers and markdown:

            normalized_headers = (
                self._headers_from_markdown(
                    markdown
                )
            )

        # --------------------------------------------------------------
        # Build normalized rows.
        # --------------------------------------------------------------

        normalized_rows = []

        for raw_row in rows:

            # ==========================================================
            # CASE 1:
            # row is already a dictionary.
            # ==========================================================

            if isinstance(
                raw_row,
                dict,
            ):

                keys = list(
                    raw_row.keys()
                )

                # ------------------------------------------------------
                # Determine whether keys are actual headers or column
                # indexes.
                # ------------------------------------------------------

                numeric_indexed = True

                indexes = []

                for key in keys:

                    key_text = str(
                        key
                    ).strip()

                    # C0 / C1 / C2
                    match = re.fullmatch(
                        r"[cC]\s*(\d+)",
                        key_text,
                    )

                    if match:
                        indexes.append(
                            int(
                                match.group(1)
                            )
                        )
                        continue

                    # 0 / 1 / 2
                    if re.fullmatch(
                        r"\d+",
                        key_text,
                    ):
                        indexes.append(
                            int(key_text)
                        )
                        continue

                    numeric_indexed = False
                    break

                # ------------------------------------------------------
                # Numeric/Cn keyed rows.
                # ------------------------------------------------------

                if (
                    numeric_indexed
                    and indexes
                    and normalized_headers
                ):

                    row_dict = {}

                    for key, value in raw_row.items():

                        key_text = str(
                            key
                        ).strip()

                        match = re.fullmatch(
                            r"[cC]\s*(\d+)",
                            key_text,
                        )

                        if match:
                            index = int(
                                match.group(1)
                            )
                        elif re.fullmatch(
                            r"\d+",
                            key_text,
                        ):
                            index = int(
                                key_text
                            )
                        else:
                            continue

                        if (
                            index
                            < len(
                                normalized_headers
                            )
                        ):
                            header = (
                                normalized_headers[
                                    index
                                ]
                            )
                        else:
                            header = (
                                f"column_{index + 1}"
                            )

                        row_dict[
                            header
                        ] = value

                    normalized_rows.append(
                        row_dict
                    )

                    continue

                # ------------------------------------------------------
                # Actual header-keyed dictionary.
                # ------------------------------------------------------

                row_dict = {}

                for key, value in raw_row.items():

                    key_text = str(
                        key
                    ).strip()

                    # --------------------------------------------------
                    # Some extractors use "C1", "C2", etc. even when
                    # headers exist.
                    # --------------------------------------------------

                    match = re.fullmatch(
                        r"[cC]\s*(\d+)",
                        key_text,
                    )

                    if match and normalized_headers:

                        index = int(
                            match.group(1)
                        )

                        if (
                            index
                            < len(
                                normalized_headers
                            )
                        ):
                            key_text = (
                                normalized_headers[
                                    index
                                ]
                            )

                    elif (
                        re.fullmatch(
                            r"\d+",
                            key_text,
                        )
                        and normalized_headers
                    ):

                        index = int(
                            key_text
                        )

                        if (
                            index
                            < len(
                                normalized_headers
                            )
                        ):
                            key_text = (
                                normalized_headers[
                                    index
                                ]
                            )

                    row_dict[
                        key_text
                    ] = value

                normalized_rows.append(
                    row_dict
                )

                continue

            # ==========================================================
            # CASE 2:
            # row is a list/tuple.
            # ==========================================================

            if isinstance(
                raw_row,
                (list, tuple),
            ):

                row_dict = {}

                for index, value in enumerate(
                    raw_row
                ):

                    if (
                        index
                        < len(
                            normalized_headers
                        )
                    ):
                        header = (
                            normalized_headers[
                                index
                            ]
                        )
                    else:
                        header = (
                            f"column_{index + 1}"
                        )

                    row_dict[
                        header
                    ] = value

                normalized_rows.append(
                    row_dict
                )

                continue

            # ==========================================================
            # CASE 3:
            # scalar row.
            # ==========================================================

            normalized_rows.append(
                {
                    "value": raw_row
                }
            )

        # --------------------------------------------------------------
        # Remove completely empty rows.
        # --------------------------------------------------------------

        normalized_rows = [
            row
            for row in normalized_rows
            if any(
                value is not None
                and str(value).strip()
                not in {
                    "",
                    "-",
                    "--",
                }
                for value in row.values()
            )
        ]

        # --------------------------------------------------------------
        # IMPORTANT:
        #
        # Some PDF extractors store a numeric column-number header row
        # such as:
        #
        #   1 | 2 | 3 | 4 | 5
        #
        # That is not a semantic header. Remove it if the actual headers
        # have already been reconstructed.
        # --------------------------------------------------------------

        if normalized_rows:

            first = normalized_rows[0]

            first_values = [
                self._norm(
                    value
                )
                for value in first.values()
                if value is not None
            ]

            if (
                first_values
                and all(
                    re.fullmatch(
                        r"\d+",
                        value,
                    )
                    for value in first_values
                )
            ):

                normalized_rows = (
                    normalized_rows[1:]
                )

        return {
            "id": getattr(
                table,
                "id",
                None,
            ),
            "page_number": getattr(
                table,
                "page_number",
                None,
            ),
            "table_index": getattr(
                table,
                "table_index",
                None,
            ),
            "title": title,
            "headers": normalized_headers,
            "rows": normalized_rows,
            "raw_rows": rows,
            "markdown": markdown,
        }

    def _headers_from_markdown(
        self,
        markdown,
    ):
        """Extract the header row from simple Markdown table text."""

        if not markdown:
            return []

        lines = [
            line.strip()
            for line in str(markdown).splitlines()
            if line.strip()
        ]

        for index, line in enumerate(lines):
            if not line.startswith("|") or "|" not in line[1:]:
                continue

            cells = [
                cell.strip()
                for cell in line.strip("|").split("|")
            ]

            if index + 1 < len(lines):
                separator = lines[index + 1]
                separator_cells = [
                    cell.strip()
                    for cell in separator.strip("|").split("|")
                ]

                if separator_cells and all(
                    re.fullmatch(r":?-{2,}:?", cell)
                    for cell in separator_cells
                ):
                    return cells

        return []

    def _normalize_headers(
        self,
        headers,
    ):
        if not headers:
            return []

        # --------------------------------------------------------------
        # Already flat.
        # --------------------------------------------------------------

        if all(
            not isinstance(
                h,
                (list, tuple)
            )
            for h in headers
        ):

            return [
                self._clean_header(
                    h
                )
                for h in headers
            ]

        # --------------------------------------------------------------
        # Multi-level headers.
        #
        # We transpose the header rows and merge each column.
        # Blank parent cells are propagated horizontally.
        # --------------------------------------------------------------

        header_rows = []

        for header in headers:

            if isinstance(
                header,
                (list, tuple)
            ):
                header_rows.append(
                    [
                        self._clean_header(
                            value
                        )
                        for value in header
                    ]
                )
            else:
                header_rows.append(
                    [
                        self._clean_header(
                            header
                        )
                    ]
                )

        width = max(
            (
                len(row)
                for row in header_rows
            ),
            default=0,
        )

        result = []

        previous = [
            ""
            for _ in range(width)
        ]

        for column in range(width):

            parts = []

            for row in header_rows:

                value = (
                    row[column]
                    if column < len(row)
                    else ""
                )

                if value:

                    parts.append(
                        value
                    )

                    previous[column] = (
                        value
                    )

                elif previous[column]:

                    # Do not blindly duplicate all parent labels.
                    # They are useful when a child header follows.
                    pass

            # Remove duplicate components while preserving order.
            unique = []

            for part in parts:

                if (
                    part
                    and part not in unique
                ):
                    unique.append(
                        part
                    )

            result.append(
                " | ".join(unique)
            )

        return result

    @staticmethod
    def _clean_header(value):
        if value is None:
            return ""

        return re.sub(
            r"\s+",
            " ",
            str(value)
            .replace(
                "\n",
                " "
            )
            .strip(),
        )

    # =========================================================================
    # JSON extraction
    # =========================================================================

    def _extract_from_table_json(
        self,
        table_json,
        facts,
        requested_fields,
        regulation_number,
        table_number,
    ):
        """
        Constraint-first extraction from one PostgreSQL table.

        The table has already been selected from regulatory source evidence.
        This method does not scan arbitrary numeric cells.  For each requested
        constraint it:

          1. uses CONSTRAINT_SPECS to decide whether this table supplies it;
          2. selects the applicable row using PlanningFacts;
          3. identifies the exact regulatory column;
          4. reads one cell from that row;
          5. returns one PostgreSQLConstraint.

        """

        regulation_number = str(regulation_number).strip()
        table_number = self._clean_table_number(table_number)

        rows = table_json.get("rows") or []
        headers = table_json.get("headers") or []

        if not rows:
            return []

        normalized_headers = self._normalize_headers(headers)

        # _table_to_json normally returns dictionaries keyed by headers.
        # Keep that representation because row applicability and branch
        # selection need the header names.
        normalized_rows = []
        for row in rows:
            if isinstance(row, dict):
                normalized_rows.append(row)
                continue

            values = self._row_values(row)
            row_dict = {}
            for index, value in enumerate(values):
                header = (
                    normalized_headers[index]
                    if index < len(normalized_headers)
                    else f"column_{index + 1}"
                )
                row_dict[header] = value
            normalized_rows.append(row_dict)

        constraints = []

        for field in requested_fields:
            spec = CONSTRAINT_SPECS.get(field)
            if not spec:
                continue

            allowed_tables = {
                self._clean_table_number(value)
                for value in spec.get("table_numbers", set())
            }

            if allowed_tables and table_number not in allowed_tables:
                continue

            kind = spec.get("kind", "table")

            # Prose/paragraph sources are intentionally not processed here.
            # They are handled by the prose-resolution path, not by table JSON.
            if kind != "table":
                continue

            # Table 6-D is a PDF-extracted multi-row table with repeated
            # physical header labels. Use the dedicated positional extractor
            # for all four setback/margin constraints.
            if table_number == "6-D" and field in {
                "front_setback",
                "rear_setback",
                "side_setback_left",
                "side_setback_right",
            }:
                setback_constraints = self._extract_6d_setback_table(
                    table_json=table_json,
                    facts=facts,
                    requested_fields=[field],
                    regulation_number=regulation_number,
                    table_number=table_number,
                )
                constraints.extend(setback_constraints)
                continue

            dimensions = tuple(spec.get("dimensions", ()))
            aliases = tuple(spec.get("column_aliases", ()))

            selected_rows = self._select_applicable_rows(
                normalized_rows,
                normalized_headers,
                facts,
                dimensions,
                field,
            )

            # Never guess between multiple different applicable rows.
            unique_rows = []
            for row in selected_rows:
                if row not in unique_rows:
                    unique_rows.append(row)
            selected_rows = unique_rows

            if len(selected_rows) != 1:
                continue

            selected_row = selected_rows[0]

            column_index = self._find_explicit_column(
                normalized_headers,
                aliases,
                field=field,
            )

            if column_index is None:
                # Some normalized rows retain semantic headers even when the
                # table header array is incomplete. Try the row itself.
                row_headers = list(selected_row.keys())
                column_index = self._find_explicit_column(
                    row_headers,
                    aliases,
                    field=field,
                )

            if column_index is None:
                continue

            row_values = list(selected_row.values())
            if column_index >= len(row_values):
                continue

            raw_value = row_values[column_index]

            if self._is_empty_regulatory_value(raw_value):
                continue

            value = self._parse_scalar(raw_value)
            if value is None:
                continue

            constraints.append(
                self._make_constraint(
                    key=field,
                    value=value,
                    unit=self._unit_for_field(field),
                    regulation_number=regulation_number,
                    table_number=table_number,
                )
            )

        return constraints

    # =========================================================================
    # Row applicability
    # =========================================================================

    def _row_matches_facts(
        self,
        row,
        facts,
    ):
        if not row:
            return False

        values = self._fact_values(
            facts
        )

        road_width = values.get(
            "road_width"
        )

        authority = (
            values.get(
                "planning_authority"
            )
            or values.get(
                "municipality"
            )
            or values.get(
                "municipal_corporation"
            )
            or values.get(
                "competent_authority"
            )
        )

        carpet_areas = (
            values.get(
                "tenement_carpet_areas"
            )
            or values.get(
                "tenement_carpet_area"
            )
        )

        if carpet_areas is not None:

            if not isinstance(
                carpet_areas,
                (list, tuple)
            ):
                carpet_areas = [
                    carpet_areas
                ]

        recognized = False

        for header, raw_value in row.items():

            if raw_value is None:
                continue

            header_norm = self._norm(
                header
            )

            text = str(
                raw_value
            ).strip()

            if not text:
                continue

            # ----------------------------------------------------------
            # Road width
            # ----------------------------------------------------------

            if (
                "road width" in header_norm
                or "width of road" in header_norm
            ):

                if road_width is not None:

                    recognized = True

                    if not self._matches_number_range(
                        text,
                        road_width,
                    ):
                        return False

            # ----------------------------------------------------------
            # Tenement/carpet area
            # ----------------------------------------------------------

            if (
                "size of tenement"
                in header_norm
                or "tenement size"
                in header_norm
                or "carpet area"
                in header_norm
            ):

                if carpet_areas:

                    recognized = True

                    numeric_areas = [
                        self._to_number(
                            area
                        )
                        for area in carpet_areas
                    ]

                    numeric_areas = [
                        area
                        for area in numeric_areas
                        if area is not None
                    ]

                    if numeric_areas and not any(
                        self._matches_number_range(
                            text,
                            area,
                        )
                        for area in numeric_areas
                    ):
                        return False

            # ----------------------------------------------------------
            # Authority
            # ----------------------------------------------------------

            if (
                "authority" in header_norm
                or (
                    "area" in header_norm
                    and (
                        "authority"
                        in self._norm(
                            text
                        )
                        or "pune"
                        in self._norm(
                            text
                        )
                        or "municipal"
                        in self._norm(
                            text
                        )
                    )
                )
            ):

                if authority:

                    recognized = True

                    if not self._authority_matches(
                        authority,
                        text,
                    ):
                        return False

            # ----------------------------------------------------------
            # Congested area
            # ----------------------------------------------------------

            if (
                "congested area"
                in header_norm
            ):

                congested = (
                    values.get(
                        "congested_area"
                    )
                )

                if congested is not None:

                    recognized = True

                    cell = self._norm(
                        text
                    )

                    if congested is True:
                        if (
                            "yes" in cell
                            or "congested" in cell
                        ):
                            pass
                    elif congested is False:
                        if (
                            "no" in cell
                            or "non congested"
                            in cell
                        ):
                            pass

        # --------------------------------------------------------------
        # Fallback: inspect complete row text for road range.
        # --------------------------------------------------------------

        row_text = " ".join(
            str(v)
            for v in row.values()
            if v is not None
        )

        if road_width is not None:

            if self._matches_number_range(
                row_text,
                road_width,
            ):
                return True

        if authority:

            if self._authority_matches(
                authority,
                row_text,
            ):
                return True

        return recognized


    def _dimension_is_available(
        self,
        facts,
        dimension,
    ):
        """
        Check whether PlanningFacts contains a usable value for a
        dimension required by the regulatory table.
        """

        value = getattr(facts, dimension, None)

        if value is None:
            return False

        if isinstance(value, str):
            return bool(value.strip())

        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)

        return True

    def _row_matches_dimension(
        self,
        row,
        headers,
        facts,
        dimension,
    ):
        """
        Match one PlanningFacts dimension against one regulatory row.

        No regulatory thresholds are hardcoded here.
        Thresholds/ranges are read from the PostgreSQL table itself.
        """

        fact_value = getattr(facts, dimension, None)

        if fact_value is None:
            return True

        row_text = " ".join(
            str(value)
            for value in row
            if value is not None
        )

        normalized_dimension = self._norm(dimension)

        # ------------------------------------------------------------
        # ROAD WIDTH
        # ------------------------------------------------------------
        if normalized_dimension in {
            "roadwidth",
            "roadwidthinmeters",
        }:
            try:
                numeric_value = float(fact_value)
            except (TypeError, ValueError):
                return False

            return self._matches_number_range(
                row_text,
                numeric_value,
            )

        # ------------------------------------------------------------
        # PLOT AREA
        # ------------------------------------------------------------
        if normalized_dimension in {
            "plotarea",
            "plotsize",
            "plotarea_sq_m",
        }:
            try:
                numeric_value = float(fact_value)
            except (TypeError, ValueError):
                return False

            return self._matches_number_range(
                row_text,
                numeric_value,
            )

        # ------------------------------------------------------------
        # HEIGHT
        # ------------------------------------------------------------
        if normalized_dimension in {
            "buildingheight",
            "buildingheightm",
            "maximumheightm",
        }:
            try:
                numeric_value = float(fact_value)
            except (TypeError, ValueError):
                return False

            return self._matches_number_range(
                row_text,
                numeric_value,
            )

        # ------------------------------------------------------------
        # CARPET AREA
        #
        # Parking tables can contain multiple tenements. The caller
        # should already provide the individual carpet areas.
        # ------------------------------------------------------------
        if normalized_dimension in {
            "tenementcarpetareas",
            "tenementcarpetarea",
        }:

            if not isinstance(fact_value, (list, tuple)):
                fact_values = [fact_value]
            else:
                fact_values = fact_value

            for area in fact_values:

                try:
                    numeric_area = float(area)
                except (TypeError, ValueError):
                    continue

                if self._matches_number_range(
                    row_text,
                    numeric_area,
                ):
                    return True

            return False

        # ------------------------------------------------------------
        # BOOLEAN DIMENSION
        # ------------------------------------------------------------
        if isinstance(fact_value, bool):

            text = self._norm(row_text)

            if fact_value:
                return any(
                    token in text
                    for token in (
                        "yes",
                        "true",
                        "congested",
                    )
                )

            return any(
                token in text
                for token in (
                    "no",
                    "false",
                    "non congested",
                    "noncongested",
                )
            )

        # ------------------------------------------------------------
        # CATEGORICAL DIMENSION
        # ------------------------------------------------------------
        fact_text = self._norm(str(fact_value))

        if not fact_text:
            return True

        row_normalized = self._norm(row_text)

        return (
            fact_text in row_normalized
            or row_normalized in fact_text
        )


    def _find_explicit_column(
        self,
        headers,
        aliases,
        field=None,
    ):
        """
        Find exactly one regulatory column matching the requested
        constraint.

        The method prefers the strongest/most specific alias.
        """

        if not headers or not aliases:
            return None

        normalized_aliases = [
            self._norm(alias)
            for alias in aliases
            if alias
        ]

        matches = []

        for index, header in enumerate(headers):

            normalized_header = self._norm(header)

            if not normalized_header:
                continue

            for alias in normalized_aliases:

                if not alias:
                    continue

                # Exact match gets strongest priority.
                if normalized_header == alias:
                    matches.append(
                        (0, index)
                    )
                    break

                # Header containing the explicit regulatory label.
                if alias in normalized_header:
                    matches.append(
                        (1, index)
                    )
                    break

        if not matches:
            return None

        matches.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        return matches[0][1]
    


    def _is_empty_regulatory_value(
        self,
        value,
    ):
        if value is None:
            return True

        text = str(value).strip().lower()

        return text in {
            "",
            "--",
            "-",
            "na",
            "n/a",
            "not applicable",
            "not available",
            "nil",
        }

    def _select_applicable_rows(
        self,
        rows,
        headers,
        facts,
        dimensions,
        field,
    ):
        """
        Select exactly the row whose table dimensions are satisfied by facts.

        A missing dimension is not treated as a mismatch.  It means that this
        particular table does not expose that dimension on the row.  We only
        require a dimension when the row actually contains evidence for it.

        This is important for multi-branch tables such as 6-G: authority is
        represented in the column/header branch, while road width is represented
        in the row.  Authority therefore must not make every 6-G row fail.
        """

        if not rows:
            return []

        values = self._fact_values(facts)
        selected = []

        for row in rows:
            if not isinstance(row, dict) or not row:
                continue

            row_text = " ".join(
                str(value)
                for value in row.values()
                if value is not None
            )

            applicable = True
            evidence_found = False

            for dimension in dimensions:
                fact_value = values.get(dimension)
                if fact_value is None:
                    continue

                dim_norm = self._norm(dimension)

                # --------------------------------------------------------
                # Road width: this is the principal row selector for 6-D/6-G.
                # --------------------------------------------------------
                if dim_norm in {"roadwidth", "roadwidthinmeters"}:
                    evidence_found = True
                    try:
                        numeric = float(fact_value)
                    except (TypeError, ValueError):
                        applicable = False
                        break

                    road_cells = []
                    for header, value in row.items():
                        header_norm = self._norm(header)
                        if (
                            "road width" in header_norm
                            or "width of road" in header_norm
                        ):
                            road_cells.append(str(value))

                    target_text = " ".join(road_cells) or row_text
                    if not self._matches_number_range(target_text, numeric):
                        applicable = False
                        break
                    continue

                # --------------------------------------------------------
                # Carpet area: parking rows have an explicit size column.
                # --------------------------------------------------------
                if dim_norm in {
                    "tenementcarpetareas",
                    "tenementcarpetarea",
                }:
                    if not isinstance(fact_value, (list, tuple)):
                        areas = [fact_value]
                    else:
                        areas = fact_value

                    area_cells = []
                    for header, value in row.items():
                        header_norm = self._norm(header)
                        if (
                            "size of tenement" in header_norm
                            or "tenement size" in header_norm
                            or "carpet area" in header_norm
                        ):
                            area_cells.append(str(value))

                    if not area_cells:
                        # Do not make non-parking tables fail merely because
                        # the dimension is not represented as a row column.
                        continue

                    evidence_found = True
                    if not any(
                        self._matches_number_range(cell, area)
                        for cell in area_cells
                        for area in areas
                        if self._to_number(area) is not None
                    ):
                        applicable = False
                        break
                    continue

                # --------------------------------------------------------
                # Authority is generally a column/header branch rather than
                # a row dimension for Table 6-G.  Branch filtering is done by
                # _header_branch_applies() during column selection.
                # --------------------------------------------------------
                if dim_norm in {
                    "planningauthority",
                    "municipality",
                    "municipalcorporation",
                    "competentauthority",
                }:
                    continue

                # --------------------------------------------------------
                # Other numeric dimensions only constrain a row if the row
                # contains a corresponding labelled dimension.
                # --------------------------------------------------------
                if dim_norm in {
                    "plotarea",
                    "plotsize",
                    "plotareasqm",
                    "buildingheight",
                    "buildingheightm",
                    "maximumheightm",
                }:
                    numeric = self._to_number(fact_value)
                    if numeric is None:
                        continue

                    labelled_cells = []
                    for header, value in row.items():
                        header_norm = self._norm(header)
                        if dim_norm.startswith("plot") and (
                            "plot" in header_norm
                            or "area" in header_norm
                        ):
                            labelled_cells.append(str(value))
                        elif dim_norm.startswith("buildingheight") and (
                            "height" in header_norm
                        ):
                            labelled_cells.append(str(value))

                    if not labelled_cells:
                        continue

                    evidence_found = True
                    if not any(
                        self._matches_number_range(cell, numeric)
                        for cell in labelled_cells
                    ):
                        applicable = False
                        break
                    continue

                # --------------------------------------------------------
                # Congested-area is relevant when the row explicitly exposes
                # a congested/non-congested dimension.
                # --------------------------------------------------------
                if dim_norm == "congestedarea":
                    cell_found = False
                    desired = bool(fact_value)

                    for header, value in row.items():
                        header_norm = self._norm(header)
                        if "congested area" not in header_norm:
                            continue

                        cell_found = True
                        evidence_found = True
                        cell = self._norm(value)

                        if desired:
                            if not (
                                "yes" in cell
                                or "congested" in cell
                            ):
                                applicable = False
                                break
                        else:
                            if not (
                                "no" in cell
                                or "non congested" in cell
                                or "noncongested" in cell
                            ):
                                applicable = False
                                break

                    if not cell_found:
                        continue
                    continue

                # --------------------------------------------------------
                # Generic categorical dimensions.
                # --------------------------------------------------------
                fact_text = self._norm(str(fact_value))
                if not fact_text:
                    continue

                matching_cells = []
                dim_aliases = {
                    "buildinguse": ("occupancy", "use", "building use"),
                    "occupancytype": ("occupancy",),
                    "zonetype": ("zone",),
                    "landusezone": ("zone", "land use"),
                    "landuseclassification": ("land use", "classification"),
                }.get(dim_norm, ())

                for header, value in row.items():
                    header_norm = self._norm(header)
                    if any(alias in header_norm for alias in dim_aliases):
                        matching_cells.append(str(value))

                if not matching_cells:
                    # No row-level evidence for this dimension. Do not reject
                    # the row; some tables encode this dimension in headers.
                    continue

                evidence_found = True
                if not any(
                    self._categorical_match(fact_text, self._norm(cell))
                    or fact_text in self._norm(cell)
                    or self._norm(cell) in fact_text
                    for cell in matching_cells
                ):
                    applicable = False
                    break

            if applicable:
                # A row with no recognized dimension evidence is not selected
                # unless the table has only one row. This prevents arbitrary
                # numeric rows from being promoted.
                if evidence_found:
                    selected.append(row)
                elif len(rows) == 1:
                    selected.append(row)

        return selected

    def _fallback_applicable_rows(
        self,
        table_json,
        facts,
        table_number,
    ):
        rows = (
            table_json.get(
                "rows"
            )
            or []
        )

        values = self._fact_values(
            facts
        )

        road_width = values.get(
            "road_width"
        )

        authority = (
            values.get(
                "planning_authority"
            )
            or values.get(
                "municipality"
            )
            or values.get(
                "municipal_corporation"
            )
            or values.get(
                "competent_authority"
            )
        )

        selected = []

        table_norm = self._norm(
            table_number
        )

        # --------------------------------------------------------------
        # Road-width tables.
        # --------------------------------------------------------------

        if (
            road_width is not None
            and table_norm in {
                "6-d",
                "6-g",
            }
        ):

            for row in rows:

                row_text = " ".join(
                    str(v)
                    for v in row.values()
                    if v is not None
                )

                if self._matches_number_range(
                    row_text,
                    road_width,
                ):
                    selected.append(
                        row
                    )

        # --------------------------------------------------------------
        # Authority table.
        # --------------------------------------------------------------

        if (
            authority
            and table_norm == "8-c"
        ):

            for row in rows:

                row_text = " ".join(
                    str(v)
                    for v in row.values()
                    if v is not None
                )

                if self._authority_matches(
                    authority,
                    row_text,
                ):
                    selected.append(
                        row
                    )

        return selected

    # =========================================================================
    # Column/value extraction
    # =========================================================================

    def _extract_field_from_row(
        self,
        row,
        aliases,
        facts=None,
    ):

        candidates = []

        for header, value in row.items():

            if value is None:
                continue

            header_norm = self._norm(
                header
            )

            if not header_norm:
                continue

            # ----------------------------------------------------------
            # Authority branch filtering.
            #
            # Table 6-G can contain multiple Basic FSI columns under
            # different authority branches.
            # ----------------------------------------------------------

            if facts is not None:

                if not self._header_branch_applies(
                    header_norm,
                    facts,
                ):
                    continue

            for alias in aliases:

                alias_norm = self._norm(
                    alias
                )

                if not alias_norm:
                    continue

                matched = (
                    alias_norm
                    in header_norm
                )

                # Basic FSI
                if (
                    alias_norm
                    == "basic fsi"
                    and "basic" in header_norm
                    and "fsi" in header_norm
                ):
                    matched = True

                # Premium FSI
                if (
                    alias_norm
                    == "premium fsi"
                    and "premium" in header_norm
                ):
                    matched = True

                # TDR
                if (
                    alias_norm
                    == "tdr fsi"
                    and (
                        "tdr"
                        in header_norm
                    )
                ):
                    matched = True

                # Maximum building potential
                if (
                    alias_norm
                    == "maximum fsi"
                    and (
                        "maximum"
                        in header_norm
                        or "building potential"
                        in header_norm
                    )
                ):
                    matched = True

                # Side margins
                if (
                    alias_norm
                    in {
                        "side setback",
                        "side setback left",
                        "side setback right",
                    }
                    and (
                        "side"
                        in header_norm
                        or "margin"
                        in header_norm
                    )
                ):
                    matched = True

                if matched:

                    parsed = self._parse_scalar(
                        value
                    )

                    if parsed is not None:
                        candidates.append(
                            parsed
                        )

                    break

        if candidates:

            unique = []

            for candidate in candidates:
                if candidate not in unique:
                    unique.append(
                        candidate
                    )

            return unique[0]

        return None

    def _header_branch_applies(
        self,
        header_norm,
        facts,
    ):
        values = self._fact_values(
            facts
        )

        authority = (
            values.get(
                "planning_authority"
            )
            or values.get(
                "municipality"
            )
            or values.get(
                "municipal_corporation"
            )
            or values.get(
                "competent_authority"
            )
        )

        if not authority:
            return True

        authority_norm = self._norm(
            authority
        )

        # --------------------------------------------------------------
        # If header clearly says remaining authorities and facts say
        # Municipal Corporation, reject it.
        # --------------------------------------------------------------

        municipal = (
            "municipal corporation"
            in authority_norm
            or "municipality"
            in authority_norm
            or "municipal corporation"
            in header_norm
        )

        remaining = (
            "remaining authorities"
            in header_norm
            or "remaining authority"
            in header_norm
            or "other authorities"
            in header_norm
        )

        if remaining and municipal:
            return False

        # --------------------------------------------------------------
        # CIDCO/municipal branch.
        # --------------------------------------------------------------

        if (
            "municipal corporation"
            in header_norm
            or "cidco"
            in header_norm
        ):

            if (
                "municipal corporation"
                in authority_norm
                or "cidco"
                in authority_norm
            ):
                return True

        return True

    # =========================================================================
    # Parking Table 8-B
    # =========================================================================


    def _extract_6d_setback_table(
        self,
        table_json,
        facts,
        requested_fields,
        regulation_number,
        table_number,
    ):
        """Deterministically extract the four setback/margin fields from UDCPR Table No.6-D.

        The PDF has these semantic columns:
            Description of the road
            Min. setback from road side in meters
            Min. side margins in meters
            Min. rear margins in meters

        The project's PostgreSQL PDF extraction stores the semantic header rows
        inside ``rows`` and the data cells in the physical positions 4, 12, 16
        and 20 respectively. This method accepts list/tuple rows as well as
        numeric/C0-style dictionaries and JSON-encoded rows.

        No regulatory numeric value is embedded here. Values are read only from
        the selected PostgreSQL TableModel row.
        """
        raw_rows = table_json.get("raw_rows") or []
        if isinstance(raw_rows, str):
            try:
                import json
                raw_rows = json.loads(raw_rows)
            except Exception:
                return []

        if not isinstance(raw_rows, (list, tuple)):
            return []

        fact_values = self._fact_values(facts)
        road_width = fact_values.get("road_width")
        if road_width is None:
            return []

        def physical_values(raw_row):
            # JSON encoded row
            if isinstance(raw_row, str):
                try:
                    import json
                    raw_row = json.loads(raw_row)
                except Exception:
                    return None

            if isinstance(raw_row, (list, tuple)):
                return list(raw_row)

            if isinstance(raw_row, dict):
                pairs = []
                numeric = True
                for key, value in raw_row.items():
                    text = str(key).strip()
                    m = re.fullmatch(r"[cC]\s*(\d+)", text)
                    if m:
                        pairs.append((int(m.group(1)), value))
                    elif re.fullmatch(r"\d+", text):
                        pairs.append((int(text), value))
                    else:
                        numeric = False
                        break
                if numeric and pairs:
                    max_index = max(i for i, _ in pairs)
                    values = [None] * (max_index + 1)
                    for i, value in pairs:
                        values[i] = value
                    return values

                # Header-keyed dictionaries: preserve insertion order.
                return list(raw_row.values())

            return None

        candidates = []

        for raw_row in raw_rows:
            row = physical_values(raw_row)
            if not row:
                continue

            # The known PDF extraction has 26 physical columns. If a row is
            # shorter, still allow a semantic fallback below, but do not invent
            # missing cells.
            text_cells = [str(v or "").strip() for v in row]
            full_text = " ".join(text_cells)
            norm_full = self._norm(full_text)

            # Skip PDF header/column-number rows.
            if "description of the road" in norm_full and "min setback" in norm_full:
                continue
            if text_cells and all(
                self._norm(v) in {str(i) for i in range(1, 9)}
                for v in text_cells if v
            ):
                continue

            # Primary location from the actual PDF physical layout.
            description = str(row[4] or "").strip() if len(row) > 4 else ""

            # Fallback: find the cell that contains the road description.
            if not description or not (
                "road" in self._norm(description)
                or "row housing" in self._norm(description)
            ):
                for cell in text_cells:
                    n = self._norm(cell)
                    if "road" in n and (
                        "width" in n or "housing" in n
                    ):
                        description = cell
                        break

            if not description:
                continue

            description_norm = self._norm(description)

            # Ignore special Row Housing unless PlanningFacts explicitly
            # identifies it. The ordinary residential test must use the
            # general road-width row.
            if "row housing" in description_norm:
                explicit_values = (
                    fact_values.get("row_housing"),
                    fact_values.get("is_row_housing"),
                    fact_values.get("building_type"),
                    fact_values.get("building_category"),
                    fact_values.get("housing_type"),
                    fact_values.get("development_type"),
                    fact_values.get("occupancy_type"),
                )
                explicit = any(
                    (isinstance(v, bool) and v)
                    or (isinstance(v, str) and "row housing" in self._norm(v))
                    for v in explicit_values if v is not None
                )
                if not explicit:
                    continue

            if not self._matches_number_range(description, road_width):
                continue

            # Primary physical positions from the PDF extraction.
            values = {
                "front_setback": row[12] if len(row) > 12 else None,
                "side_setback_left": row[16] if len(row) > 16 else None,
                "side_setback_right": row[16] if len(row) > 16 else None,
                "rear_setback": row[20] if len(row) > 20 else None,
            }

            # A valid Table 6-D data row must contain at least one of the three
            # setback columns. This prevents header rows from becoming data.
            if not any(v is not None and str(v).strip() not in {"", "-", "--"}
                       for v in values.values()):
                continue

            candidates.append((row, values, description))

        # Deterministic selection: for ordinary residential use at 12 m, the
        # general '<15 m' row is selected; special Row Housing is only selected
        # with explicit facts. Never silently choose between two rows.
        if len(candidates) != 1:
            return []

        _row, values, _description = candidates[0]
        constraints = []

        for field in requested_fields:
            if field not in values:
                continue
            raw_value = values[field]
            if self._is_empty_regulatory_value(raw_value):
                continue
            value = self._parse_scalar(raw_value)
            if value is None:
                continue

            constraints.append(
                self._make_constraint(
                    key=field,
                    value=value,
                    unit="m",
                    regulation_number=regulation_number,
                    table_number=table_number,
                )
            )

        return constraints

    def _extract_side_setback_table(
        self,
        table_json,
        facts,
        requested_fields,
        regulation_number,
        table_number,
    ):
        rows = table_json.get("rows") or []
        headers = table_json.get("headers") or []

        if not rows:
            return []

        normalized_headers = self._normalize_headers(headers)
        normalized_rows = []

        for row in rows:
            if isinstance(row, dict):
                normalized_rows.append(row)
                continue

            values = self._row_values(row)
            normalized_rows.append({
                normalized_headers[i] if i < len(normalized_headers)
                else f"column_{i + 1}": value
                for i, value in enumerate(values)
            })

        selected_rows = self._select_applicable_rows(
            normalized_rows,
            normalized_headers,
            facts,
            ("road_width",),
            "side_setback",
        )

        if len(selected_rows) != 1:
            return []

        row = selected_rows[0]

        key = self._find_explicit_column(
            list(row.keys()),
            (
                "minimum side margins",
                "min side margins",
                "side margins",
                "side margin",
                "side setback",
            ),
            field="side_setback",
        )

        if key is None:
            return []

        value = self._parse_scalar(row.get(key))
        if value is None:
            return []

        constraints = []

        for field in requested_fields:
            constraints.append(
                self._make_constraint(
                    key=field,
                    value=value,
                    unit="m",
                    regulation_number=regulation_number,
                    table_number=table_number,
                )
            )

        return constraints

    def _make_constraint(
        self,
        key,
        value,
        unit,
        regulation_number,
        table_number,
    ):
        return PostgreSQLConstraint(
            key=key,
            value=value,
            unit=unit,
            source_rule_id=(
                "postgresql:"
                f"{regulation_number}:"
                f"{table_number}"
            ),
            regulation_id=str(
                regulation_number
            ),
            rule_name=(
                f"UDCPR "
                f"{regulation_number} "
                f"Table "
                f"{table_number}"
            ),
            category="authoritative_table",
            priority=1,
            status="verified",
            reason=(
                "Value extracted deterministically "
                "from PostgreSQL authoritative table."
            ),
            metadata={
                "source": "postgresql",
                "regulation_number": str(
                    regulation_number
                ),
                "table_number": str(
                    table_number
                ),
            },
        )

    @staticmethod
    def _unit_for_field(
        field_name,
    ):
        if (
            "setback" in field_name
            or "height" in field_name
            or "margin" in field_name
        ):
            return "m"

        if "parking" in field_name:
            return "spaces"

        return None

    def _deduplicate_constraints(
        self,
        constraints,
        result,
    ):
        by_key = {}

        for constraint in constraints:

            existing = by_key.get(
                constraint.key
            )

            if existing is None:
                by_key[
                    constraint.key
                ] = constraint
                continue

            if (
                existing.value
                == constraint.value
            ):
                continue

            # Side setback left/right can legitimately be supplied
            # by the same table value.
            if constraint.key in {
                "side_setback_left",
                "side_setback_right",
            }:
                continue

            result.warnings.append(
                "Conflicting PostgreSQL values "
                f"for {constraint.key}: "
                f"{existing.value} vs "
                f"{constraint.value}"
            )

        return list(
            by_key.values()
        )

    # =========================================================================
    # Facts
    # =========================================================================

    @staticmethod
    def _fact_values(facts):
        if isinstance(facts, dict):
            values = dict(facts)
        else:
            values = {}

            for name in (
                "road_width",
                "planning_authority",
                "municipality",
                "municipal_corporation",
                "competent_authority",

                "zone",
                "zone_type",
                "land_use",
                "land_use_zone",
                "land_use_classification",

                "occupancy",
                "occupancy_type",
                "building_use",

                "project_type",
                "development_type",

                "congested_area",

                "group_housing",
                "row_housing",
                "is_row_housing",

                "building_type",
                "building_category",
                "housing_type",

                "tenement_carpet_areas",
                "tenement_carpet_area",

                "plot_area",
                "building_height",
            ):
                if hasattr(facts, name):
                    values[name] = getattr(facts, name)

        # ------------------------------------------------------------------
        # Normalize common aliases so the resolver has one canonical value.
        # ------------------------------------------------------------------

        if values.get("occupancy") is None:
            values["occupancy"] = (
                values.get("occupancy_type")
                or values.get("building_use")
            )

        if values.get("land_use") is None:
            values["land_use"] = (
                values.get("land_use_zone")
                or values.get("land_use_classification")
            )

        if values.get("tenement_carpet_areas") is None:
            values["tenement_carpet_areas"] = values.get(
                "tenement_carpet_area"
            )

        if values.get("planning_authority") is None:
            values["planning_authority"] = (
                values.get("municipality")
                or values.get("municipal_corporation")
                or values.get("competent_authority")
            )

        return values
 

    # =========================================================================
    # Numeric parsing
    # =========================================================================

    @staticmethod
    def _parse_scalar(
        value,
    ):
        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return value

        if isinstance(
            value,
            (int, float),
        ):
            return value

        text = str(
            value
        ).strip()

        if not text:
            return None

        normalized = text.lower()

        if normalized in {
            "-",
            "--",
            "—",
            "–",
            "na",
            "n/a",
            "nil",
            "none",
            "not applicable",
            "not available",
        }:
            return None

        cleaned = (
            text
            .replace(
                ",",
                "",
            )
            .replace(
                "\n",
                " ",
            )
            .strip()
        )

        match = re.search(
            r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)",
            cleaned,
        )

        if match:

            try:
                number = float(
                    match.group(0)
                )

                if number.is_integer():
                    return int(
                        number
                    )

                return number

            except (
                TypeError,
                ValueError,
            ):
                pass

        return cleaned

    @staticmethod
    def _to_number(
        value,
    ):
        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return None

        if isinstance(
            value,
            (int, float),
        ):
            return float(
                value
            )

        match = re.search(
            r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)",
            str(value),
        )

        if not match:
            return None

        try:
            return float(
                match.group(0)
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _integer_if_possible(
        value,
    ):
        numeric = float(
            value
        )

        if numeric.is_integer():
            return int(
                numeric
            )

        return numeric

    # =========================================================================
    # Range matching
    # =========================================================================

    def _matches_number_range(
        self,
        text,
        value,
    ):
        if value is None:
            return False

        target = self._to_number(
            value
        )

        if target is None:
            return False

        text = str(
            text or ""
        ).lower()

        # --------------------------------------------------------------
        # Extract numeric values.
        # --------------------------------------------------------------

        numbers = [
            float(x)
            for x in re.findall(
                r"\d+(?:\.\d+)?",
                text,
            )
        ]

        if not numbers:
            return False

        # --------------------------------------------------------------
        # Above / greater than.
        # --------------------------------------------------------------

        if (
            "above" in text
            or "greater than" in text
            or "more than" in text
        ):

            lower = numbers[0]

            if (
                "below" in text
                or "upto" in text
                or "up to" in text
            ) and len(numbers) >= 2:

                upper = numbers[1]

                return (
                    target >= lower
                    and target < upper
                )

            return target >= lower

        # --------------------------------------------------------------
        # Below / less than.
        # --------------------------------------------------------------

        if (
            "below" in text
            or "less than" in text
        ):

            upper = numbers[-1]

            if len(numbers) >= 2:
                lower = numbers[0]

                return (
                    target >= lower
                    and target < upper
                )

            return target < upper

        # --------------------------------------------------------------
        # Upto.
        # --------------------------------------------------------------

        if (
            "upto" in text
            or "up to" in text
        ):

            upper = numbers[-1]

            return target <= upper

        # --------------------------------------------------------------
        # Between / range using two numbers.
        # --------------------------------------------------------------

        if len(numbers) >= 2:

            lower = numbers[0]
            upper = numbers[1]

            # Explicit "<" upper bound.
            if (
                "<" in text
                and (
                    "m" in text
                    or "meter" in text
                )
            ):
                return (
                    target >= lower
                    and target < upper
                )

            return (
                target >= lower
                and target <= upper
            )

        # --------------------------------------------------------------
        # Single number.
        # --------------------------------------------------------------

        return abs(
            target - numbers[0]
        ) < 1e-9

    # =========================================================================
    # Authority matching
    # =========================================================================

    def _authority_matches(
        self,
        authority,
        text,
    ):
        authority_norm = self._norm(
            authority
        )

        text_norm = self._norm(
            text
        )

        if not authority_norm:
            return False

        if authority_norm in text_norm:
            return True

        # Pune-specific textual representation.
        if (
            "pune" in authority_norm
            and "pune" in text_norm
        ):
            return True

        if (
            "pcmc" in authority_norm
            and "pcmc" in text_norm
        ):
            return True

        # Municipal corporation branch.
        if (
            "municipal corporation"
            in authority_norm
            and
            "municipal corporation"
            in text_norm
        ):
            return True

        return self._categorical_match(
            authority_norm,
            text_norm,
        )

    @staticmethod
    def _categorical_match(
        left,
        right,
    ):
        left_tokens = {
            token
            for token in re.findall(
                r"[a-z0-9]+",
                str(left).lower(),
            )
            if len(token) > 2
        }

        right_tokens = {
            token
            for token in re.findall(
                r"[a-z0-9]+",
                str(right).lower(),
            )
            if len(token) > 2
        }

        if not left_tokens or not right_tokens:
            return False

        return bool(
            left_tokens
            & right_tokens
        )

    # =========================================================================
    # Normalization
    # =========================================================================

    @staticmethod
    def _norm(
        value,
    ):
        return re.sub(
            r"\s+",
            " ",
            str(
                value or ""
            )
            .replace(
                "\n",
                " ",
            )
            .replace(
                "\r",
                " ",
            )
            .strip()
            .lower(),
        )
