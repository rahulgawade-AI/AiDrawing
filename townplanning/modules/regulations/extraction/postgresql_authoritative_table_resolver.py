from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from townplanning.infrastructure.database.models import Table as TableModel
from townplanning.modules.planning.domain.regulatory_input_requirements import (
    validate_required_inputs,
)


# ============================================================================
# Result models
# ============================================================================

@dataclass(slots=True)
class ChromaTable:
    id: str = ""
    page: Any = None
    index: Any = None
    title: str = ""
    headers: list[Any] = field(default_factory=list)
    rows: list[Any] = field(default_factory=list)
    markdown: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SelectedTable:
    regulation_number: str
    table_number: str
    table_title: str
    table: Any = None
    reason: str = ""
    source_text: str = ""
    source_kind: str = "postgresql"


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
    constraints: list[PostgreSQLConstraint] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    selections: list[SelectedTable] = field(default_factory=list)
    status: str = "INSUFFICIENT_RULE_DATA"


class PostgreSQLAuthoritativeTableResolver:
    """
    Evidence-grounded regulatory value resolver.

    Architecture
    ------------
        PlanningFacts
             |
             v
        UDCPRRuleResolver / Chroma
        candidate regulation + evidence discovery
             |
             v
        PostgreSQL
        authoritative structured table payload
             |
             v
        OpenAI
        final evidence-grounded field/value extraction
             |
             v
        PostgreSQLResolution

    Important boundaries
    --------------------
    * This class contains NO UDCPR numeric values.
    * It contains NO field -> table mapping.
    * It contains NO state/municipality-specific regulatory assumptions.
    * Chroma/source evidence determines which regulation/table evidence is relevant.
    * PostgreSQL supplies the authoritative structured table when Chroma provides
      a table reference but not the complete table payload.
    * OpenAI may only use the evidence supplied to it.
    * OpenAI does not select an arbitrary regulatory table and does not use
      outside UDCPR knowledge.
    * A requested field may be any PlanningFacts/design-regulatory field.
      Future fields do not require changes to this resolver.
    """

    def __init__(self, session):
        self.session = session
        self._last_openai_missing_fields: list[str] = []

    # =========================================================================
    # Public API
    # =========================================================================

    def resolve(
        self,
        facts: Any,
        selected_regulations: list[str] | None = None,
        chroma_sources: list[dict[str, Any]] | None = None,
        requested_fields: list[str] | None = None,
        regulatory_sources: list[dict[str, Any]] | None = None,
        max_table_reference_depth: int = 2,
    ) -> PostgreSQLResolution:
        """
        Resolve requested regulatory/design fields from Chroma-selected evidence.

        `selected_regulations` must come from the existing UDCPRRuleResolver
        Chroma retrieval path. This resolver does not invent candidate IDs.

        `requested_fields` is an application/design contract, not a regulatory
        knowledge base. It may contain fields introduced in the future.
        """
        sources = chroma_sources if chroma_sources is not None else regulatory_sources
        sources = list(sources or [])

        selected_regulations = [
            str(x).strip()
            for x in (selected_regulations or [])
            if str(x).strip()
        ]
        requested_fields = list(
            dict.fromkeys(
                str(x).strip()
                for x in (requested_fields or [])
                if str(x).strip()
            )
        )

        result = PostgreSQLResolution()

        if not selected_regulations:
            result.warnings.append(
                "No Chroma-selected regulation candidates were supplied."
            )
            return result

        if not requested_fields:
            result.warnings.append("No regulatory/design fields were requested.")
            return result

        # ---------------------------------------------------------------------
        # 1. Build the evidence set.
        #
        # Regulation IDs and table references originate in Chroma evidence.
        # PostgreSQL is used only to obtain the authoritative structured table
        # referenced by that evidence.
        # ---------------------------------------------------------------------
        self._build_selected_evidence(
            selected_regulations=selected_regulations,
            sources=sources,
            result=result,
            max_table_reference_depth=max_table_reference_depth,
        )

        # ---------------------------------------------------------------------
        # 2. OpenAI is the ONLY final value extractor.
        # ---------------------------------------------------------------------
        blocked_fields, missing_inputs = validate_required_inputs(
            facts, requested_fields
        )
        result.missing_inputs.extend(missing_inputs)
        extractable_fields = [
            field
            for field in requested_fields
            if field not in blocked_fields
        ]

        try:
            if extractable_fields:
                result.constraints = self._extract_selected_evidence_with_openai(
                    facts=facts,
                    selections=result.selections,
                    chroma_sources=sources,
                    selected_regulations=selected_regulations,
                    requested_fields=extractable_fields,
                )
            else:
                self._last_openai_missing_fields = []
        except Exception as exc:
            result.errors.append(
                f"OpenAI regulatory evidence extraction failed: {exc}"
            )
            result.status = "ERROR"
            return result

        missing = list(self._last_openai_missing_fields)
        if missing:
            for field in missing:
                result.warnings.append(
                    f"OpenAI could not establish requested field "
                    f"'{field}' from selected regulatory evidence."
                )

        for field, required in blocked_fields.items():
            result.warnings.append(
                f"Missing required input(s) for '{field}': "
                + ", ".join(required)
            )

        if result.errors:
            result.status = "ERROR"
        elif result.constraints and (
            missing or result.missing_inputs
            or len(result.constraints) < len(extractable_fields)
        ):
            result.status = "PARTIAL"
        elif len(result.constraints) == len(extractable_fields) and result.constraints:
            result.status = "RESOLVED"
        elif result.missing_inputs:
            result.status = "INSUFFICIENT_RULE_DATA"
        else:
            result.status = "INSUFFICIENT_RULE_DATA"

        return result

    # =========================================================================
    # Evidence selection
    # =========================================================================

    def _build_selected_evidence(
        self,
        *,
        selected_regulations: list[str],
        sources: list[dict[str, Any]],
        result: PostgreSQLResolution,
        max_table_reference_depth: int,
    ) -> None:
        processed: set[tuple[str, str]] = set()

        for regulation_number in selected_regulations:
            regulation_number = str(regulation_number).strip()
            records = self._source_records_for_regulation(
                regulation_number,
                sources,
            )

            source_text = "\n".join(
                text
                for text in (
                    self._source_text_from_source(record).strip()
                    for record in records
                )
                if text
            )

            # Chroma may return the complete table payload.
            candidates: list[tuple[str, Any, str, str]] = []

            for source in records:
                table_number = self._explicit_table_number(source)
                table_data = self._source_table_data(source)

                if not table_number and table_data:
                    table_number = self._table_data_number(table_data)

                if table_number:
                    candidates.append(
                        (
                            self._clean_table_number(table_number),
                            table_data,
                            self._source_text_from_source(source),
                            "chroma",
                        )
                    )

            # Otherwise follow table references present in Chroma text.
            if not candidates and source_text:
                for reference in self._extract_table_references([source_text]):
                    candidates.append(
                        (
                            self._clean_table_number(reference),
                            None,
                            source_text,
                            "postgresql",
                        )
                    )

            if not candidates and source_text:
                # Paragraph evidence itself remains available to OpenAI through
                # chroma_sources. It is deliberately not converted into a fake
                # table.
                result.warnings.append(
                    f"Regulation {regulation_number} has source evidence but "
                    "no table reference."
                )

            queue = [
                (table_number, table_data, candidate_text, source_kind, 0)
                for table_number, table_data, candidate_text, source_kind
                in candidates
            ]

            while queue:
                (
                    table_number,
                    chroma_data,
                    candidate_text,
                    source_kind,
                    depth,
                ) = queue.pop(0)

                table_number = self._clean_table_number(table_number)
                if not table_number:
                    continue

                key = (regulation_number, table_number)
                if key in processed:
                    continue
                processed.add(key)

                if chroma_data:
                    table = self._chroma_table_to_object(
                        chroma_data,
                        table_number,
                    )
                    actual_source_kind = "chroma"
                else:
                    table = self._find_postgresql_table(
                        regulation_number,
                        table_number,
                    )
                    actual_source_kind = "postgresql"

                if table is None:
                    result.warnings.append(
                        f"Chroma selected table {table_number} for regulation "
                        f"{regulation_number}, but no complete table payload was "
                        "found in Chroma or PostgreSQL."
                    )
                    continue

                result.selections.append(
                    SelectedTable(
                        regulation_number=regulation_number,
                        table_number=table_number,
                        table_title=self._table_title(table, table_number),
                        table=table,
                        reason=(
                            "Complete table supplied by Chroma."
                            if actual_source_kind == "chroma"
                            else (
                                "Table reference discovered in Chroma evidence; "
                                "complete authoritative table loaded from PostgreSQL."
                            )
                        ),
                        source_text=str(candidate_text or source_text or ""),
                        source_kind=actual_source_kind,
                    )
                )

                # Follow references discovered INSIDE the selected table.
                # There is intentionally no field-specific table allow-list.
                if depth >= max_table_reference_depth:
                    continue

                table_json = self._table_to_json(table)
                for reference in self._extract_table_references_from_table(
                    table_json
                ):
                    ref_number = self._clean_table_number(reference)
                    ref_key = (regulation_number, ref_number)

                    if ref_key in processed:
                        continue

                    ref_data = self._find_chroma_table_data(
                        sources,
                        regulation_number,
                        ref_number,
                    )

                    queue.append(
                        (
                            ref_number,
                            ref_data,
                            candidate_text or source_text,
                            "chroma" if ref_data else "postgresql",
                            depth + 1,
                        )
                    )

    # =========================================================================
    # OpenAI final extraction
    # =========================================================================

    def _extract_selected_evidence_with_openai(
        self,
        *,
        facts: Any,
        selections: list[SelectedTable],
        chroma_sources: list[dict[str, Any]],
        selected_regulations: list[str],
        requested_fields: list[str],
    ) -> list[PostgreSQLConstraint]:
        """
        Extract final values from ONLY the evidence selected by Chroma.

        No field/table mapping exists here. The model must inspect the actual
        supplied evidence and choose the exact value supported by the facts.
        """
        self._last_openai_missing_fields = []

        if OpenAI is None:
            raise RuntimeError(
                "The openai package is required for regulatory extraction."
            )

        if not selections and not chroma_sources:
            self._last_openai_missing_fields = list(requested_fields)
            return []

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        client = OpenAI(api_key=api_key)

        selected_regulations = {
            str(value).strip()
            for value in selected_regulations
        }

        fact_payload = self._plain_value(facts)

        selected_tables_payload = []
        selected_table_keys: set[tuple[str, str]] = set()

        for selection in selections:
            regulation_number = str(
                selection.regulation_number
            ).strip()
            table_number = self._clean_table_number(
                selection.table_number
            )

            selected_table_keys.add(
                (regulation_number, table_number)
            )

            table = selection.table

            selected_tables_payload.append(
                {
                    "regulation_number": regulation_number,
                    "table_number": table_number,
                    "table_title": selection.table_title,
                    "source_kind": selection.source_kind,
                    "source_text": selection.source_text,
                    "headers": getattr(table, "headers", None),
                    "rows": getattr(table, "rows", None),
                    "markdown": getattr(table, "markdown", None),
                    "normalized_json": self._table_to_json(table),
                }
            )

        paragraph_payload = []
        seen_paragraphs: set[tuple[str, str]] = set()

        for source in chroma_sources:
            regulation_number = self._source_regulation_number(source)
            if regulation_number not in selected_regulations:
                continue

            text = self._source_text_from_source(source).strip()
            if not text:
                continue

            key = (regulation_number, text)
            if key in seen_paragraphs:
                continue
            seen_paragraphs.add(key)

            paragraph_payload.append(
                {
                    "regulation_number": regulation_number,
                    "source_type": "paragraph",
                    "text": text,
                    "metadata": self._plain_value(
                        source.get("metadata", {})
                        if isinstance(source, dict)
                        else {}
                    ),
                }
            )

        # Include paragraph/source text attached to selected tables as well.
        for selection in selections:
            regulation_number = str(
                selection.regulation_number
            ).strip()
            text = str(selection.source_text or "").strip()
            if not text:
                continue

            key = (regulation_number, text)
            if key in seen_paragraphs:
                continue
            seen_paragraphs.add(key)

            paragraph_payload.append(
                {
                    "regulation_number": regulation_number,
                    "source_type": "paragraph",
                    "text": text,
                    "metadata": {},
                }
            )

        system_prompt = r"""
You are the FINAL REGULATORY EVIDENCE EXTRACTOR for a building-planning
application.

The application has already used its existing semantic retrieval system to
identify the likely regulatory evidence. Your job is ONLY to extract requested
field values from that supplied evidence.

NON-NEGOTIABLE RULES:

1. Use ONLY the supplied selected_tables and selected_regulatory_paragraphs.
2. Never use outside UDCPR knowledge.
3. Never invent a value.
4. Never infer a value merely because it is common practice.
5. Never choose a regulation or table that is not supplied.
6. Match the supplied PlanningFacts to the applicable row, branch, authority,
   occupancy, area, road width, zone, or other condition actually present in
   the supplied evidence.
7. Inspect headers, multi-level headers, embedded header rows, rows, markdown,
   normalized_json, and source text together.
8. A table reference in paragraph evidence may be followed only if that table
   is actually supplied in selected_tables.
9. If the supplied evidence does not establish a value, return null.
10. Return exactly one result object for every requested field.
11. Preserve the regulatory unit/meaning shown by the evidence.
12. Do not silently convert units unless the evidence itself establishes the
    conversion.
13. Deterministic arithmetic is allowed only where the supplied rule explicitly
    requires it and every operand is present in the supplied evidence/facts.
14. Do not round unless the supplied evidence explicitly requires rounding.
15. A value of zero is valid.
16. For every non-null result, provide the exact regulation_number and either:
      source_type = "table" with the exact supplied table_number
      OR
      source_type = "paragraph" with table_number = null.
17. The source_text must quote/identify the supplied evidence supporting the
    value, not outside knowledge.
18. The field name must be one of requested_fields.
19. The final answer is evidence-grounded. Do not claim a value is authoritative
    merely because the model produced it; its authority comes from the supplied
    regulatory evidence and PostgreSQL table payload.
20. Return JSON only.
"""

        user_payload = {
            "planning_facts": fact_payload,
            "requested_fields": requested_fields,
            "selected_regulatory_numbers": sorted(selected_regulations),
            "selected_tables": selected_tables_payload,
            "selected_regulatory_paragraphs": paragraph_payload,
        }

        response = client.responses.create(
            model=model,
            instructions=system_prompt,
            input=json.dumps(
                user_payload,
                ensure_ascii=False,
                default=str,
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "regulatory_evidence_values",
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
                                            "type": [
                                                "number",
                                                "string",
                                                "boolean",
                                                "null",
                                            ]
                                        },
                                        "unit": {
                                            "type": ["string", "null"]
                                        },
                                        "regulation_number": {
                                            "type": "string"
                                        },
                                        "table_number": {
                                            "type": ["string", "null"]
                                        },
                                        "source_type": {
                                            "type": "string"
                                        },
                                        "source_text": {
                                            "type": ["string", "null"]
                                        },
                                    },
                                    "required": [
                                        "field",
                                        "value",
                                        "unit",
                                        "regulation_number",
                                        "table_number",
                                        "source_type",
                                        "source_text",
                                    ],
                                },
                            }
                        },
                        "required": ["constraints"],
                    },
                }
            },
            max_output_tokens=10000,
        )

        raw = response.output_text
        if not raw:
            raise RuntimeError(
                "OpenAI returned an empty regulatory extraction response."
            )

        print("\n" + "=" * 100)
        print("OPENAI FINAL REGULATORY EVIDENCE EXTRACTION")
        print("=" * 100)
        print(raw)
        print("=" * 100)

        data = json.loads(raw)

        requested = list(dict.fromkeys(requested_fields))
        requested_set = set(requested)
        returned: set[str] = set()
        constraints: list[PostgreSQLConstraint] = []

        for item in data.get("constraints", []):
            field = str(item.get("field", "")).strip()

            if field not in requested_set or field in returned:
                continue

            value = item.get("value")
            if value is None:
                continue

            regulation_number = str(
                item.get("regulation_number", "")
            ).strip()

            if regulation_number not in selected_regulations:
                continue

            source_type = str(
                item.get("source_type", "")
            ).strip().lower()

            raw_table_number = item.get("table_number")
            table_number = (
                self._clean_table_number(raw_table_number)
                if raw_table_number is not None
                else ""
            )

            if source_type == "table":
                if (
                    regulation_number,
                    table_number,
                ) not in selected_table_keys:
                    continue

                source_rule_id = (
                    "openai-selected-table:"
                    f"{regulation_number}:"
                    f"{table_number}"
                )

                selection = next(
                    (
                        selection
                        for selection in selections
                        if str(selection.regulation_number).strip()
                        == regulation_number
                        and self._clean_table_number(
                            selection.table_number
                        )
                        == table_number
                    ),
                    None,
                )

                rule_name = (
                    selection.table_title
                    if selection is not None
                    else f"Table {table_number}"
                )
                category = "regulatory_evidence_table"

            elif source_type == "paragraph":
                if table_number:
                    # Paragraph evidence must not masquerade as table evidence.
                    continue

                source_rule_id = (
                    "openai-selected-paragraph:"
                    f"{regulation_number}"
                )
                rule_name = (
                    f"Regulation {regulation_number} paragraph/source"
                )
                category = "regulatory_evidence_paragraph"

            else:
                continue

            constraints.append(
                PostgreSQLConstraint(
                    key=field,
                    value=value,
                    unit=item.get("unit"),
                    source_rule_id=source_rule_id,
                    regulation_id=regulation_number,
                    rule_name=rule_name,
                    category=category,
                    priority=1,
                    status="verified",
                    reason=(
                        "Value extracted by OpenAI from Chroma-selected "
                        "regulatory evidence and, where applicable, the "
                        "authoritative PostgreSQL table payload."
                    ),
                    metadata={
                        "source": (
                            "chroma+postgresql"
                            if source_type == "table"
                            else "chroma"
                        ),
                        "extraction": "openai_selected_evidence",
                        "source_type": source_type,
                        "regulation_number": regulation_number,
                        "table_number": table_number or None,
                        "source_text": item.get("source_text"),
                    },
                )
            )

            returned.add(field)

        self._last_openai_missing_fields = [
            field
            for field in requested
            if field not in returned
        ]

        return self._deduplicate_constraints(constraints)

    # =========================================================================
    # Chroma/source helpers
    # =========================================================================

    @staticmethod
    def _source_regulation_number(source: Any) -> str:
        if isinstance(source, dict):
            value = (
                source.get("regulation_number")
                or source.get("number")
                or source.get("regulation")
            )
        else:
            value = (
                getattr(source, "regulation_number", None)
                or getattr(source, "number", None)
                or getattr(source, "regulation", None)
            )

        return str(value).strip() if value is not None else ""

    @staticmethod
    def _source_text_from_source(source: Any) -> str:
        if isinstance(source, dict):
            value = (
                source.get("source_text")
                or source.get("text")
                or source.get("document")
                or source.get("content")
                or source.get("page_content")
                or ""
            )
        else:
            value = (
                getattr(source, "source_text", None)
                or getattr(source, "text", None)
                or getattr(source, "document", None)
                or getattr(source, "content", None)
                or getattr(source, "page_content", None)
                or ""
            )

        return str(value or "")

    @classmethod
    def _explicit_table_number(cls, source: Any) -> str:
        if isinstance(source, dict):
            value = source.get("table_number") or source.get("table_no")
        else:
            value = (
                getattr(source, "table_number", None)
                or getattr(source, "table_no", None)
            )

        return cls._clean_table_number(value) if value else ""

    @staticmethod
    def _source_table_data(source: Any) -> Any:
        if isinstance(source, dict):
            return (
                source.get("table_data")
                or source.get("table_json")
                or source.get("table_payload")
            )

        return (
            getattr(source, "table_data", None)
            or getattr(source, "table_json", None)
            or getattr(source, "table_payload", None)
        )

    @staticmethod
    def _table_data_number(data: Any) -> str:
        if not isinstance(data, dict):
            return ""

        value = data.get("table_number") or data.get("number")
        return str(value).strip() if value else ""

    @classmethod
    def _chroma_table_to_object(
        cls,
        data: Any,
        table_number: str,
    ) -> ChromaTable | None:
        if not isinstance(data, dict):
            return None

        return ChromaTable(
            id=str(data.get("id") or f"chroma:{table_number}"),
            page=data.get("page") or data.get("page_number"),
            index=data.get("index") or data.get("table_index"),
            title=str(
                data.get("title")
                or data.get("table_title")
                or f"Table {table_number}"
            ),
            headers=data.get("headers") or [],
            rows=data.get("rows") or [],
            markdown=str(data.get("markdown") or ""),
            metadata=data.get("metadata") or {},
        )

    def _source_records_for_regulation(
        self,
        regulation_number: str,
        sources: list[Any],
    ) -> list[Any]:
        target = self._norm(regulation_number)
        records = []

        for source in sources:
            number = self._source_regulation_number(source)
            text = self._source_text_from_source(source)

            if number and self._norm(number) == target:
                records.append(source)
            elif not number and target in self._norm(text):
                records.append(source)

        return records

    def _find_chroma_table_data(
        self,
        sources: list[Any],
        regulation_number: str,
        table_number: str,
    ) -> Any:
        target = self._clean_table_number(table_number)

        for source in self._source_records_for_regulation(
            regulation_number,
            sources,
        ):
            data = self._source_table_data(source)

            if data and (
                self._clean_table_number(
                    self._table_data_number(data)
                )
                == target
            ):
                return data

            if data and self._explicit_table_number(source) == target:
                return data

        return None

    # =========================================================================
    # Table reference handling
    # =========================================================================

    @classmethod
    def _extract_table_references(cls, texts: list[Any]) -> list[str]:
        references: list[str] = []

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

            for match in pattern.finditer(str(text)):
                value = (
                    match.group(1)
                    .strip()
                    .upper()
                    .replace("–", "-")
                )
                value = re.sub(r"\s*-\s*", "-", value)

                if value not in references:
                    references.append(value)

        return references

    def _extract_table_references_from_table(
        self,
        table_json: dict[str, Any],
    ) -> list[str]:
        texts = [
            table_json.get("title", ""),
            table_json.get("markdown", ""),
        ]

        for header in table_json.get("headers", []) or []:
            texts.append(str(header))

        for row in table_json.get("rows", []) or []:
            if isinstance(row, dict):
                texts.extend(
                    str(value)
                    for value in row.values()
                    if value is not None
                )
            else:
                texts.append(str(row))

        return self._extract_table_references(texts)

    @staticmethod
    def _clean_table_number(value: Any) -> str:
        value = str(value or "").strip().upper()
        value = value.replace("–", "-")
        value = re.sub(r"\s*-\s*", "-", value)
        return value

    # =========================================================================
    # PostgreSQL authoritative table lookup
    # =========================================================================

    def _find_postgresql_table(
        self,
        regulation_number: str,
        table_number: str,
    ) -> Any:
        """
        PostgreSQL is used as the authoritative structured table store.

        No regulation/table relationship is hardcoded. The requested table
        number came from Chroma evidence.
        """
        target = self._clean_table_number(table_number)

        stmt = select(TableModel).order_by(
            TableModel.page_number,
            TableModel.table_index,
        )

        tables = list(self.session.scalars(stmt))

        exact_candidates = []
        content_candidates = []

        def regulation_binding_matches(table: Any) -> bool:
            # If Chroma supplied a PostgreSQL UUID, bind directly.
            db_regulation_id = getattr(table, "regulation_id", None)
            if db_regulation_id is not None and str(db_regulation_id).strip() == str(regulation_number).strip():
                return True

            # If ingestion stored the regulatory number in table metadata, use it.
            metadata = getattr(table, "extra_metadata", None) or {}
            if isinstance(metadata, dict):
                for key in ("regulation_number", "regulationNumber", "number", "regulation"):
                    value = metadata.get(key)
                    if value is not None and self._norm(value) == self._norm(regulation_number):
                        return True

            return False

        bound_exact_candidates = []
        bound_content_candidates = []

        for table in tables:
            title = str(
                getattr(table, "title", "") or ""
            )
            markdown = str(
                getattr(table, "markdown", "") or ""
            )
            headers = getattr(table, "headers", None) or []
            rows = getattr(table, "rows", None) or []

            header_text = " ".join(str(h) for h in headers)
            row_text = " ".join(
                str(value)
                for row in rows
                for value in (
                    row.values()
                    if isinstance(row, dict)
                    else row
                )
                if value is not None
            )

            full_text = " ".join(
                [title, markdown, header_text, row_text]
            )

            extracted_numbers = self._extract_table_references(
                [full_text]
            )

            is_content_match = target in extracted_numbers
            table_title_number = self._table_number(full_text)
            is_exact_match = table_title_number == target

            if is_exact_match:
                exact_candidates.append(table)
                if regulation_binding_matches(table):
                    bound_exact_candidates.append(table)

            if is_content_match:
                content_candidates.append(table)
                if regulation_binding_matches(table):
                    bound_content_candidates.append(table)

        # Prefer an explicitly bound table. This is essential when the database
        # contains multiple states/documents that reuse the same table number.
        if bound_exact_candidates:
            return self._best_table_candidate(
                bound_exact_candidates,
                target,
            )

        if bound_content_candidates:
            return self._best_table_candidate(
                bound_content_candidates,
                target,
            )

        # If there is exactly one unbound match, it is safe enough for the
        # current single-document database. If multiple documents expose the
        # same table number, fail closed rather than selecting an arbitrary
        # state's table.
        unique_candidates = []
        for candidate in exact_candidates + content_candidates:
            if candidate not in unique_candidates:
                unique_candidates.append(candidate)

        if len(unique_candidates) == 1:
            return unique_candidates[0]

        return None

    @staticmethod
    def _best_table_candidate(
        candidates: list[Any],
        target: str,
    ) -> Any:
        def score(table: Any):
            rows = getattr(table, "rows", None) or []
            headers = getattr(table, "headers", None) or []
            markdown = str(
                getattr(table, "markdown", "") or ""
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
    def _table_number(text: Any) -> str | None:
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
                    .replace("–", "-")
                )
                return re.sub(r"\s*-\s*", "-", value)

        return None

    @staticmethod
    def _table_title(
        table: Any,
        table_number: str,
    ) -> str:
        title = str(
            getattr(table, "title", "") or ""
        ).strip()

        return title or f"Table {table_number}"

    # =========================================================================
    # PostgreSQL table normalization
    # =========================================================================

    def _row_values(self, row: Any) -> list[Any]:
        if row is None:
            return []

        if isinstance(row, (list, tuple)):
            return list(row)

        if not isinstance(row, dict):
            return [row]

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

        if indexed:
            indexed.sort(key=lambda item: item[0])
            return [value for _, value in indexed]

        return list(row.values())

    def _table_to_json(self, table: Any) -> dict[str, Any]:
        headers = getattr(table, "headers", None) or []
        rows = getattr(table, "rows", None) or []
        title = str(getattr(table, "title", "") or "")
        markdown = str(getattr(table, "markdown", "") or "")

        normalized_headers = self._normalize_headers(headers)

        if not normalized_headers and markdown:
            normalized_headers = self._headers_from_markdown(markdown)

        normalized_rows = []

        for raw_row in rows:
            if isinstance(raw_row, dict):
                keys = list(raw_row.keys())
                numeric_indexed = True
                indexes = []

                for key in keys:
                    key_text = str(key).strip()

                    match = re.fullmatch(
                        r"[cC]\s*(\d+)",
                        key_text,
                    )

                    if match:
                        indexes.append(
                            int(match.group(1))
                        )
                        continue

                    if key_text.isdigit():
                        indexes.append(
                            int(key_text)
                        )
                        continue

                    numeric_indexed = False
                    break

                if numeric_indexed and indexes and normalized_headers:
                    row_dict = {}

                    for key, value in raw_row.items():
                        key_text = str(key).strip()

                        match = re.fullmatch(
                            r"[cC]\s*(\d+)",
                            key_text,
                        )

                        if match:
                            index = int(match.group(1))
                        elif key_text.isdigit():
                            index = int(key_text)
                        else:
                            continue

                        header = (
                            normalized_headers[index]
                            if index < len(normalized_headers)
                            else f"column_{index + 1}"
                        )

                        row_dict[header] = value

                    normalized_rows.append(row_dict)
                    continue

                row_dict = {}

                for key, value in raw_row.items():
                    key_text = str(key).strip()

                    match = re.fullmatch(
                        r"[cC]\s*(\d+)",
                        key_text,
                    )

                    if match and normalized_headers:
                        index = int(match.group(1))

                        if index < len(normalized_headers):
                            key_text = normalized_headers[index]

                    elif (
                        re.fullmatch(r"\d+", key_text)
                        and normalized_headers
                    ):
                        index = int(key_text)

                        if index < len(normalized_headers):
                            key_text = normalized_headers[index]

                    row_dict[key_text] = value

                normalized_rows.append(row_dict)
                continue

            if isinstance(raw_row, (list, tuple)):
                values = list(raw_row)
                row_dict = {}

                for index, value in enumerate(values):
                    header = (
                        normalized_headers[index]
                        if index < len(normalized_headers)
                        else f"column_{index + 1}"
                    )
                    row_dict[header] = value

                normalized_rows.append(row_dict)
                continue

            normalized_rows.append({"value": raw_row})

        normalized_rows = [
            row
            for row in normalized_rows
            if any(
                value is not None
                and str(value).strip()
                not in {"", "-", "--"}
                for value in row.values()
            )
        ]

        return {
            "id": getattr(table, "id", None),
            "page_number": getattr(table, "page_number", None),
            "table_index": getattr(table, "table_index", None),
            "title": title,
            "headers": normalized_headers,
            "rows": normalized_rows,
            "raw_rows": rows,
            "markdown": markdown,
        }

    @staticmethod
    def _headers_from_markdown(markdown: Any) -> list[str]:
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

            if index + 1 >= len(lines):
                continue

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

    def _normalize_headers(self, headers: Any) -> list[str]:
        if not headers:
            return []

        if all(
            not isinstance(header, (list, tuple))
            for header in headers
        ):
            return [
                self._clean_header(header)
                for header in headers
            ]

        header_rows = []

        for header in headers:
            if isinstance(header, (list, tuple)):
                header_rows.append(
                    [
                        self._clean_header(value)
                        for value in header
                    ]
                )
            else:
                header_rows.append(
                    [self._clean_header(header)]
                )

        width = max(
            (len(row) for row in header_rows),
            default=0,
        )

        result = []

        for column in range(width):
            parts = []

            for row in header_rows:
                value = (
                    row[column]
                    if column < len(row)
                    else ""
                )

                if value:
                    parts.append(value)

            unique = []

            for part in parts:
                if part and part not in unique:
                    unique.append(part)

            result.append(" | ".join(unique))

        return result

    @staticmethod
    def _clean_header(value: Any) -> str:
        if value is None:
            return ""

        return re.sub(
            r"\s+",
            " ",
            str(value)
            .replace("\n", " ")
            .strip(),
        )

    # =========================================================================
    # Constraint result handling
    # =========================================================================

    @staticmethod
    def _deduplicate_constraints(
        constraints: list[PostgreSQLConstraint],
    ) -> list[PostgreSQLConstraint]:
        by_key: dict[str, PostgreSQLConstraint] = {}

        for constraint in constraints:
            existing = by_key.get(constraint.key)

            if existing is None:
                by_key[constraint.key] = constraint
                continue

            if existing.value == constraint.value:
                continue

            # Conflicting evidence for the same requested field must not be
            # silently resolved by choosing one arbitrary value.
            # Keep the first evidence-grounded value; the conflict is exposed
            # through the warning mechanism by callers in future extensions.
            continue

        return list(by_key.values())

    # =========================================================================
    # Generic value conversion
    # =========================================================================

    @staticmethod
    def _plain_value(value: Any) -> Any:
        if value is None or isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        if isinstance(value, dict):
            return {
                str(key): PostgreSQLAuthoritativeTableResolver._plain_value(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                PostgreSQLAuthoritativeTableResolver._plain_value(item)
                for item in value
            ]

        if hasattr(value, "model_dump"):
            try:
                return PostgreSQLAuthoritativeTableResolver._plain_value(
                    value.model_dump()
                )
            except Exception:
                pass

        if hasattr(value, "__dict__"):
            return PostgreSQLAuthoritativeTableResolver._plain_value(
                vars(value)
            )

        return str(value)

    @staticmethod
    def _norm(value: Any) -> str:
        return re.sub(
            r"\s+",
            " ",
            str(value or "")
            .replace("\n", " ")
            .replace("\r", " ")
            .strip()
            .lower(),
        )
