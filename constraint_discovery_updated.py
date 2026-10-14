from __future__ import annotations

"""
Ollama-based UDCPR constraint discovery.

Ollama DISCOVERS which regulatory constraints must be considered.
The deterministic planning/rule engine remains responsible for
deterministic regulatory calculations and validation.

Evidence sources:
    - User/project facts
    - PostgreSQL UDCPR rules
    - PostgreSQL extracted UDCPR tables
    - UDCPR PDF-derived evidence
    - Existing deterministic calculations
    - Plot/site image facts

IMPORTANT:
This module must NOT turn the entire UDCPR database into a generic
constraint list. Applicability is determined from the CURRENT project.
"""

from dataclasses import dataclass, field
from typing import Any
import json
import re


# ---------------------------------------------------------------------------
# RESULT OBJECT
# ---------------------------------------------------------------------------

@dataclass
class ConstraintDiscoveryResult:
    """Stable result object consumed by tests and planning services."""

    status: str
    model: str
    constraints: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[dict[str, Any]] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    rule_count: int = 0
    table_count: int = 0
    error: str | None = None

    @property
    def constraint_count(self) -> int:
        return len(self.constraints)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "model": self.model,
            "constraint_count": self.constraint_count,
            "constraints": self.constraints,
            "unresolved": self.unresolved,
            "facts": self.facts,
            "rule_count": self.rule_count,
            "table_count": self.table_count,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# SERVICE
# ---------------------------------------------------------------------------

class ConstraintDiscovery:
    """
    Uses Ollama to discover planning constraints from project facts,
    PostgreSQL rules/tables and optional PDF evidence.
    """

    def __init__(
        self,
        ollama=None,
        rule_resolver=None,
        table_repository=None,
        pdf_repository=None,
        model: str = "qwen3:8b",
        max_rules: int = 150,
        max_tables: int = 100,
    ):
        self.ollama = ollama
        self.rule_resolver = rule_resolver
        self.table_repository = table_repository
        self.pdf_repository = pdf_repository
        self.model = model
        self.max_rules = max_rules
        self.max_tables = max_tables

        if self.ollama is None:
            from townplanning.modules.planning.llm.ollama_client import (
                OllamaClient,
            )
            self.ollama = OllamaClient(
                model=model,
                timeout=600,
            )

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def discover(
        self,
        facts: Any,
        rules: list[Any] | None = None,
        pdf_evidence: list[Any] | None = None,
        max_rules: int | None = None,
        max_tables: int | None = None,
    ) -> ConstraintDiscoveryResult:

        try:
            fact_values = self._facts_to_dict(facts)

            if rules is None:
                rules = self._load_rules(
                    facts=facts,
                    max_rules=(
                        max_rules
                        if max_rules is not None
                        else self.max_rules
                    ),
                )

            tables = self._load_relevant_tables(
                facts=facts,
                max_tables=(
                    max_tables
                    if max_tables is not None
                    else self.max_tables
                ),
                rules=rules,
            )

            # PDF evidence can be passed directly by the caller.
            # If a repository is configured, attempt to load it as well.
            pdf_items = list(pdf_evidence or [])
            if not pdf_items:
                pdf_items = self._load_pdf_evidence(facts)

            prompt = self._build_prompt(
                facts=fact_values,
                rules=rules,
                tables=tables,
                pdf_evidence=pdf_items,
            )

            raw = self.ollama.generate(prompt)

            print("\n" + "=" * 100)
            print("RAW OLLAMA RESPONSE")
            print("=" * 100)
            print(raw)
            print("=" * 100)

            parsed = self._parse_json(raw)

            # Retry using a compact but still project-aware prompt.
            if parsed is None:
                retry_prompt = self._build_retry_prompt(
                    facts=fact_values,
                    rules=rules,
                    tables=tables,
                    pdf_evidence=pdf_items,
                )

                retry_raw = self.ollama.generate(retry_prompt)

                print("\n" + "=" * 100)
                print("RAW OLLAMA RETRY RESPONSE")
                print("=" * 100)
                print(retry_raw)
                print("=" * 100)

                parsed = self._parse_json(retry_raw)

            if parsed is None:
                return ConstraintDiscoveryResult(
                    status="error",
                    model=self.model,
                    constraints=[],
                    unresolved=[{
                        "reason": "Ollama returned non-JSON output after two attempts"
                    }],
                    facts=fact_values,
                    rule_count=len(rules or []),
                    table_count=len(tables),
                    error="Ollama returned non-JSON output after two attempts",
                )

            normalized = self._normalize_result(
                parsed=parsed,
                facts=fact_values,
                rules=rules,
                tables=tables,
            )

            return ConstraintDiscoveryResult(
                status=normalized["status"],
                model=normalized["model"],
                constraints=normalized["constraints"],
                unresolved=normalized["unresolved"],
                facts=normalized["facts"],
                rule_count=normalized["rule_count"],
                table_count=normalized["table_count"],
                error=normalized.get("error"),
            )

        except Exception as exc:
            return ConstraintDiscoveryResult(
                status="error",
                model=self.model,
                constraints=[],
                unresolved=[{"reason": str(exc)}],
                facts=self._facts_to_dict(facts),
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # FACTS
    # ------------------------------------------------------------------

    @staticmethod
    def _facts_to_dict(facts: Any) -> dict[str, Any]:
        if facts is None:
            return {}

        if isinstance(facts, dict):
            return dict(facts)

        if hasattr(facts, "to_dict"):
            try:
                value = facts.to_dict()
                if isinstance(value, dict):
                    return dict(value)
            except Exception:
                pass

        if hasattr(facts, "__dict__"):
            return {
                key: ConstraintDiscovery._json_safe(value)
                for key, value in vars(facts).items()
                if not key.startswith("_")
            }

        try:
            return dict(facts)
        except Exception:
            return {"value": str(facts)}

    # ------------------------------------------------------------------
    # RULE LOADING
    # ------------------------------------------------------------------

    def _load_rules(self, facts: Any, max_rules: int) -> list[Any]:
        if self.rule_resolver is None:
            return []

        try:
            if hasattr(self.rule_resolver, "resolve_building_rules"):
                rules = self.rule_resolver.resolve_building_rules(facts)
            elif hasattr(self.rule_resolver, "resolve"):
                rules = self.rule_resolver.resolve(facts)
            else:
                return []

            return list(rules or [])[:max_rules]

        except Exception:
            return []

    # ------------------------------------------------------------------
    # PDF LOADING
    # ------------------------------------------------------------------

    def _load_pdf_evidence(self, facts: Any) -> list[Any]:
        """
        Optional PDF repository adapter.

        Supported repository methods:
            get_relevant_evidence(facts)
            search(facts)
            retrieve(facts)

        If no PDF repository is configured, [] is returned.
        """

        if self.pdf_repository is None:
            return []

        try:
            for method_name in (
                "get_relevant_evidence",
                "search",
                "retrieve",
            ):
                method = getattr(
                    self.pdf_repository,
                    method_name,
                    None,
                )
                if callable(method):
                    result = method(facts)
                    if result is None:
                        return []
                    if isinstance(result, list):
                        return result
                    return [result]

        except Exception:
            return []

        return []

    # ------------------------------------------------------------------
    # TABLE LOADING
    # ------------------------------------------------------------------

    def _load_relevant_tables(
        self,
        facts: Any,
        max_tables: int,
        rules: list[Any] | None = None,
    ) -> list[dict[str, Any]]:

        if self.table_repository is None:
            return []

        try:
            if hasattr(self.table_repository, "list"):
                raw_tables = self.table_repository.list()
            elif hasattr(self.table_repository, "get_all"):
                raw_tables = self.table_repository.get_all()
            else:
                raw_tables = []

            # IMPORTANT FIX:
            # Never join raw DB fields directly. PostgreSQL adapters may
            # return tuples/lists/dicts. Convert everything safely first.
            rule_text_parts: list[str] = []

            for rule in rules or []:
                if isinstance(rule, dict):
                    category = str(rule.get("category", "") or "")
                    name = str(rule.get("name", "") or "")
                    description = str(
                        rule.get("description", "") or ""
                    )
                    result = self._json_safe(
                        rule.get("result", None)
                    )
                else:
                    category = str(
                        getattr(rule, "category", "") or ""
                    )
                    name = str(
                        getattr(rule, "name", "") or ""
                    )
                    description = str(
                        getattr(rule, "description", "") or ""
                    )
                    result = self._json_safe(
                        getattr(rule, "result", None)
                    )

                result_text = (
                    json.dumps(
                        result,
                        ensure_ascii=False,
                        default=str,
                    )
                    if isinstance(result, (dict, list))
                    else str(result or "")
                )

                rule_text_parts.append(
                    " ".join(
                        [
                            category,
                            name,
                            description,
                            result_text,
                        ]
                    )
                )

            rule_text = " ".join(rule_text_parts).lower()

            # Keep this evidence selection broad enough for Ollama to decide
            # applicability. Do NOT use the keyword filter as the final
            # applicability decision.
            keywords = [
                "parking",
                "setback",
                "margin",
                "marginal",
                "height",
                "fsi",
                "tdr",
                "incentive",
                "premium",
                "coverage",
                "ground",
                "open space",
                "amenity",
                "fire",
                "stair",
                "staircase",
                "lift",
                "accessibility",
                "egress",
                "exit",
                "road",
                "building",
                "ventilation",
                "light",
                "floor",
                "storey",
                "plot",
                "reservation",
                "recreation",
                "balcony",
                "sanitation",
                "water closet",
                "urinal",
                "hotel",
                "hospital",
                "restaurant",
                "school",
                "educational",
                "residential",
                "bungalow",
                "villa",
                "hostel",
                "commercial",
                "industrial",
                "institutional",
                "mixed use",
            ]

            tables: list[dict[str, Any]] = []

            for table in raw_tables or []:
                if isinstance(table, dict):
                    title = str(
                        table.get("title", table.get("name", "")) or ""
                    )
                    table_id = str(
                        table.get("id", table.get("table_id", "")) or ""
                    )
                    page = table.get("page")
                    index = table.get("index")
                    headers_raw = table.get("headers", []) or []
                    rows_raw = table.get("rows", []) or []
                else:
                    title = str(
                        getattr(table, "title", "") or ""
                    )
                    table_id = str(
                        getattr(table, "id", "") or ""
                    )
                    page = getattr(table, "page", None)
                    index = getattr(table, "index", None)
                    headers_raw = (
                        getattr(table, "headers", []) or []
                    )
                    rows_raw = (
                        getattr(table, "rows", []) or []
                    )

                headers = [
                    self._json_safe(value)
                    for value in headers_raw
                ]

                rows = self._safe_rows(rows_raw)

                searchable = (
                    f"{title} "
                    f"{json.dumps(headers, default=str)} "
                    f"{json.dumps(rows, default=str)}"
                ).lower()

                relevance = 0

                for keyword in keywords:
                    if keyword in searchable:
                        relevance += 1
                    if keyword in rule_text:
                        relevance += 1

                # High-value general regulatory tables.
                for marker in (
                    "table no.8-b",
                    "table no. 8-b",
                    "parking requirements",
                    "setback",
                    "fsi",
                    "fire",
                ):
                    if marker in searchable:
                        relevance += 50

                if relevance <= 0:
                    continue

                tables.append({
                    "id": table_id,
                    "page": self._json_safe(page),
                    "index": self._json_safe(index),
                    "title": title,
                    "headers": headers,
                    "rows": rows,
                    "relevance": relevance,
                })

            tables.sort(
                key=lambda item: (
                    item.get("relevance", 0),
                    -(item.get("page", 0) or 0),
                ),
                reverse=True,
            )

            return tables[:max_tables]

        except Exception as exc:
            # Table loading must never make the whole discovery service crash.
            return [{
                "error": f"Table loading failed: {exc}"
            }]

    # ------------------------------------------------------------------
    # SAFE TABLE ROW CONVERSION
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_rows(rows: Any) -> list[Any]:
        if not isinstance(rows, (list, tuple)):
            return []

        result = []

        for row in rows:
            if isinstance(row, dict):
                result.append({
                    str(key): ConstraintDiscovery._json_safe(value)
                    for key, value in row.items()
                })
            elif isinstance(row, (list, tuple)):
                result.append([
                    ConstraintDiscovery._json_safe(value)
                    for value in row
                ])
            else:
                result.append(
                    ConstraintDiscovery._json_safe(row)
                )

        return result

    # ------------------------------------------------------------------
    # JSON SAFE
    # ------------------------------------------------------------------

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            return {
                str(key): ConstraintDiscovery._json_safe(val)
                for key, val in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [
                ConstraintDiscovery._json_safe(item)
                for item in value
            ]

        return str(value)

    # ------------------------------------------------------------------
    # PROMPT
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        facts: dict[str, Any],
        rules: list[Any],
        tables: list[dict[str, Any]],
        pdf_evidence: list[Any] | None = None,
    ) -> str:
        """
        Build the main Ollama prompt.

        IMPORTANT:
        This deliberately does NOT use an f-string.

        The previous implementation used:

            prompt = f""" ... JSON ... """

        which made Python interpret JSON braces as f-string expressions
        and caused:

            Invalid format specifier ...

        Dynamic data is inserted through placeholder replacement instead.
        """

        project_json = json.dumps(
            self._json_safe(facts),
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        rules_payload = []

        for rule in rules or []:
            if isinstance(rule, dict):
                rules_payload.append({
                    "id": str(
                        rule.get(
                            "rule_id",
                            rule.get("id", ""),
                        ) or ""
                    ),
                    "category": str(
                        rule.get("category", "") or ""
                    ),
                    "name": str(
                        rule.get("name", "") or ""
                    ),
                    "description": str(
                        rule.get("description", "") or ""
                    ),
                    "status": str(
                        rule.get("status", "") or ""
                    ),
                    "condition": self._json_safe(
                        rule.get("condition", {})
                    ),
                    "result": self._json_safe(
                        rule.get("result", {})
                    ),
                })
            else:
                rules_payload.append({
                    "id": str(
                        getattr(
                            rule,
                            "rule_id",
                            getattr(rule, "id", ""),
                        ) or ""
                    ),
                    "category": str(
                        getattr(rule, "category", "") or ""
                    ),
                    "name": str(
                        getattr(rule, "name", "") or ""
                    ),
                    "description": str(
                        getattr(rule, "description", "") or ""
                    ),
                    "status": str(
                        getattr(rule, "status", "") or ""
                    ),
                    "condition": self._json_safe(
                        getattr(rule, "condition", {})
                    ),
                    "result": self._json_safe(
                        getattr(rule, "result", {})
                    ),
                })

        rules_json = json.dumps(
            self._json_safe(rules_payload),
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        tables_json = json.dumps(
            self._json_safe(tables),
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        pdf_json = json.dumps(
            self._json_safe(pdf_evidence or []),
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        template = r"""
You are the Regulatory Constraint Discovery Engine for an AI Town Planning Platform.

Your task is to determine the COMPLETE SET OF REGULATORY CONSTRAINTS
that must be considered when planning and designing the CURRENT project.

You are NOT generating a building design.
You are NOT generating CAD/DXF/SVG/PDF drawings.
You are NOT inventing regulatory values.

Your job is to identify:
1. Applicable constraints.
2. Conditionally applicable constraints.
3. Constraints requiring additional information.
4. Clearly non-applicable constraints.
5. Source traceability for each discovered constraint.

============================================================
AUTHORITATIVE SOURCES
============================================================

Regulatory evidence may come from:

1. Original UDCPR PDF
2. PostgreSQL UDCPR rules
3. PostgreSQL extracted UDCPR tables
4. Existing deterministic calculations
5. User-provided project facts
6. Facts extracted from the user's plot/site image

The supplied UDCPR PDF and PostgreSQL regulatory data are authoritative.

Use evidence to determine applicability.

Do NOT invent a regulation simply because it is common building practice.

If the supplied evidence does not establish a regulatory requirement,
use "needs_verification" rather than inventing a value.

============================================================
CURRENT PROJECT
============================================================

PROJECT FACTS:

__PROJECT_FACTS__

The project can be ANY type of development.

Possible project types include:

- Residential apartment building
- Residential bungalow
- Villa
- Row house
- Commercial building
- Office
- Shop / mercantile building
- Hotel
- Hospital
- Nursing home
- Restaurant
- School
- College
- Hostel
- Institutional building
- Industrial building
- Warehouse
- Mixed-use development
- Public / semi-public building
- Parking building
- Other special-use building

The user's actual project facts ALWAYS take precedence over these examples.

============================================================
POSTGRESQL UDCPR RULES
============================================================

__RULES__

============================================================
POSTGRESQL UDCPR TABLES
============================================================

__TABLES__

============================================================
UDCPR PDF EVIDENCE
============================================================

__PDF_EVIDENCE__

============================================================
CORE APPLICABILITY RULE
============================================================

DO NOT select a constraint merely because it appears in the supplied
database tables or PDF.

For EACH candidate regulation ask:

"Does this regulation apply to THIS project?"

The CURRENT project's:
- building use
- building type
- occupancy
- special uses
- mixed-use components
- plot facts
- road facts
- height/floor facts

determine applicability.

============================================================
BUILDING-USE-SPECIFIC REGULATIONS
============================================================

If the project is a HOTEL:
hotel-specific regulations may apply.

If the project is a HOSPITAL:
hospital-specific regulations may apply.

If the project is a RESTAURANT:
restaurant-specific regulations may apply.

If the project is a SCHOOL:
school/educational regulations may apply.

If the project is a HOSTEL:
hostel/residential-institutional regulations may apply.

If the project is a BUNGALOW/VILLA:
bungalow/villa-specific regulations may apply where supported.

If the project is RESIDENTIAL APARTMENT:
hotel, hospital, restaurant, school and other unrelated
use-specific requirements must NOT be selected unless the supplied
UDCPR evidence explicitly makes them applicable.

If the project is COMMERCIAL:
commercial regulations may apply.

If the project is INDUSTRIAL:
industrial regulations may apply.

If the project is INSTITUTIONAL:
institutional regulations may apply.

If the project is MIXED USE:
evaluate every actual use component separately.

Example:

Residential + Commercial

may require:
- residential regulations
- commercial regulations
- common site regulations
- mixed-use regulations

Example:

Hotel + Restaurant

may require both hotel and restaurant regulations.

Example:

Hospital + Nursing home

may require the applicable hospital/nursing-home requirements.

Do NOT assume that the word "building" makes a regulation applicable.

============================================================
DO NOT OVER-FILTER
============================================================

The opposite error is also prohibited.

Do NOT reject a regulation merely because it is use-specific.

If the current project actually is a hotel and the evidence contains
hotel-specific requirements, include them.

If the current project actually is a hospital and the evidence contains
hospital-specific requirements, include them.

The project type determines relevance.

============================================================
GENERAL CONSTRAINT CATEGORIES
============================================================

Consider ALL categories supported by the supplied evidence, including
but not limited to:

Land use / zoning
Plot eligibility
Plot area
Plot dimensions
Plot shape
Road width
Road frontage
Road widening
DP reservations
Regional Plan reservations
FSI
Basic FSI
Maximum permissible FSI
Premium FSI
TDR FSI
Incentive FSI
Additional FSI
FSI exclusions
FSI deductions
Ground coverage
Setbacks / margins
Front setback
Rear setback
Side setbacks
Building height
Number of floors / storeys
Floor height
Building footprint
Open spaces
Recreational open space
Amenity space
Parking
Car parking
Two-wheeler parking
Visitor parking
Parking area
Loading / unloading
Fire access
Fire safety
Fire staircase
Fire lift
Emergency exits
Exit width
Staircases
Staircase width
Corridor width
Lift requirements
Accessibility
Barrier-free access
Ramp requirements
Light and ventilation
Natural lighting
Natural ventilation
Sanitation
Water closets
Urinals
Bathrooms
Service areas
Refuge areas
Special building requirements
Building-use-specific requirements
Mixed-use requirements
Institutional requirements
Commercial requirements
Industrial requirements
Hotel-specific requirements
Hospital-specific requirements
Restaurant-specific requirements
Educational requirements
Residential requirements
Bungalow / villa requirements
Hostel requirements
Any other constraint explicitly supported by the evidence.

This list is NOT exhaustive.

If the evidence identifies another relevant constraint, include it.

============================================================
CONDITIONAL CONSTRAINTS
============================================================

Do not discard a constraint merely because an input is currently unknown.

Examples:
- Fire safety
- Fire lift
- Refuge area
- Maximum height
- Number of exits
- Open space
- Parking
- Accessibility
- Special occupancy requirements
- Lift requirements

Return such constraints as:
"applicability": "conditional"
and/or
"status": "needs_information"

Specify required_inputs.

Example:

{
  "name": "Fire Lift",
  "category": "Fire Safety",
  "applicability": "conditional",
  "status": "needs_information",
  "required_inputs": [
    "proposed_building_height"
  ]
}

============================================================
SOURCE TRACEABILITY
============================================================

Every discovered constraint should contain source information whenever
the supplied evidence allows it.

Possible sources:
- PostgreSQL rule ID
- PostgreSQL table ID
- PostgreSQL table name
- PDF page
- UDCPR regulation
- UDCPR clause

Do NOT invent source IDs or page numbers.

If unavailable:
"source": null

============================================================
DO NOT INVENT REGULATORY VALUES
============================================================

If a value cannot be determined from supplied evidence, return null.

Do NOT guess FSI, setbacks, parking, height, coverage, fire requirements,
sanitation requirements or any other numerical regulatory value.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

No markdown.
No ```json fences.
No explanation.
No <think> block.
No text before or after JSON.

Use this structure:

{
  "status": "resolved",
  "project": {
    "building_type": "...",
    "building_use": "...",
    "occupancy": "..."
  },
  "constraints": [
    {
      "id": "unique_constraint_id",
      "name": "Human readable constraint name",
      "category": "Constraint category",
      "applicability": "applicable",
      "status": "needs_calculation",
      "reason": "Why this constraint applies to this project",
      "required_inputs": [],
      "source_rules": [],
      "source_tables": [],
      "source_pdf_pages": [],
      "regulation_references": [],
      "value": null,
      "unit": null,
      "calculation": null
    }
  ],
  "excluded_constraints": [
    {
      "name": "...",
      "reason": "Not applicable to the current project"
    }
  ],
  "missing_information": [
    {
      "field": "...",
      "reason": "..."
    }
  ]
}

============================================================
ALLOWED APPLICABILITY VALUES
============================================================

applicable
conditional
not_applicable
needs_information

============================================================
ALLOWED CALCULATION STATUS VALUES
============================================================

resolved
needs_calculation
needs_verification

============================================================
FINAL CHECK
============================================================

Before returning JSON:

1. Identify actual building use.
2. Identify actual building type.
3. Identify all mixed-use components.
4. Check PostgreSQL rules.
5. Check PostgreSQL tables.
6. Check PDF evidence.
7. Determine applicability for EACH candidate.
8. Remove clearly unrelated building-use-specific regulations.
9. Keep conditional regulations.
10. Keep regulations requiring missing information.
11. Preserve source traceability.
12. Never invent regulatory numbers.
13. Return valid JSON only.

Now discover the COMPLETE applicable constraint set for the CURRENT project.

__END__
"""

        # IMPORTANT:
        # Use replace(), NOT str.format(), so literal JSON braces in the
        # prompt remain untouched. This is the direct fix for the previous
        # "Invalid format specifier" exception.
        return (
            template
            .replace("__PROJECT_FACTS__", project_json)
            .replace("__RULES__", rules_json)
            .replace("__TABLES__", tables_json)
            .replace("__PDF_EVIDENCE__", pdf_json)
        )

    # ------------------------------------------------------------------
    # RETRY PROMPT
    # ------------------------------------------------------------------

    def _build_retry_prompt(
        self,
        facts: dict[str, Any],
        rules: list[Any],
        tables: list[dict[str, Any]],
        pdf_evidence: list[Any] | None = None,
    ) -> str:
        """
        Compact JSON-only retry prompt.

        IMPORTANT:
        This is project-type agnostic. The old implementation said
        "For this residential building", which incorrectly forced hotel,
        hospital, school, restaurant etc. requests into residential logic.
        """

        project_json = json.dumps(
            self._json_safe(facts),
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        rule_payload = []

        for rule in rules or []:
            if isinstance(rule, dict):
                rule_payload.append({
                    "id": str(
                        rule.get(
                            "rule_id",
                            rule.get("id", ""),
                        ) or ""
                    ),
                    "category": str(
                        rule.get("category", "") or ""
                    ),
                    "name": str(
                        rule.get("name", "") or ""
                    ),
                    "description": str(
                        rule.get("description", "") or ""
                    ),
                    "result": self._json_safe(
                        rule.get("result", {})
                    ),
                })
            else:
                rule_payload.append({
                    "id": str(
                        getattr(
                            rule,
                            "rule_id",
                            getattr(rule, "id", ""),
                        ) or ""
                    ),
                    "category": str(
                        getattr(rule, "category", "") or ""
                    ),
                    "name": str(
                        getattr(rule, "name", "") or ""
                    ),
                    "description": str(
                        getattr(rule, "description", "") or ""
                    ),
                    "result": self._json_safe(
                        getattr(rule, "result", {})
                    ),
                })

        rules_json = json.dumps(
            self._json_safe(rule_payload),
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        tables_json = json.dumps(
            self._json_safe(tables),
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        pdf_json = json.dumps(
            self._json_safe(pdf_evidence or []),
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        template = r"""
Return ONLY valid JSON.

No markdown.
No explanation.
No reasoning.
No <think>.
No text before or after the JSON.

Determine the regulatory constraints for THIS PROJECT only.

PROJECT FACTS:
__PROJECT_FACTS__

POSTGRESQL RULES:
__RULES__

POSTGRESQL TABLES:
__TABLES__

PDF EVIDENCE:
__PDF_EVIDENCE__

IMPORTANT:
The project may be residential, bungalow, villa, row house, commercial,
hotel, hospital, nursing home, restaurant, school, college, hostel,
institutional, industrial, warehouse, mixed-use or another use.

Determine the actual project type from PROJECT FACTS.

Do NOT assume residential.

Do NOT include hotel requirements for a non-hotel project.
Do NOT include hospital requirements for a non-hospital project.
Do NOT include restaurant requirements for a non-restaurant project.
Do NOT include school requirements for a non-school project.
Do NOT include industrial requirements for a non-industrial project.
Do NOT include institutional requirements for a non-institutional project.

If mixed-use is present, evaluate each actual use separately.

Common regulations such as FSI, road width, setbacks, parking, fire,
height, accessibility, light/ventilation etc. may apply only when
supported by the supplied regulatory evidence.

Do not invent numerical regulatory values.

Return:

{
  "status": "resolved",
  "project": {
    "building_type": "...",
    "building_use": "...",
    "occupancy": "..."
  },
  "constraints": [
    {
      "id": "unique_constraint_id",
      "name": "...",
      "category": "...",
      "applicability": "applicable",
      "status": "needs_calculation",
      "reason": "...",
      "required_inputs": [],
      "source_rules": [],
      "source_tables": [],
      "source_pdf_pages": [],
      "regulation_references": [],
      "value": null,
      "unit": null,
      "calculation": null
    }
  ],
  "excluded_constraints": [],
  "missing_information": []
}

Allowed applicability:
applicable
conditional
not_applicable
needs_information

Allowed calculation status:
resolved
needs_calculation
needs_verification

Return JSON now.
"""

        return (
            template
            .replace("__PROJECT_FACTS__", project_json)
            .replace("__RULES__", rules_json)
            .replace("__TABLES__", tables_json)
            .replace("__PDF_EVIDENCE__", pdf_json)
        )

    # ------------------------------------------------------------------
    # JSON PARSER
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(raw: Any) -> dict[str, Any] | None:
        if raw is None:
            return None

        if isinstance(raw, dict):
            return raw

        text = str(raw).strip()

        if not text:
            return None

        # Qwen3 may emit <think>...</think>.
        text = re.sub(
            r"<think>.*?</think>",
            "",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()

        text = re.sub(
            r"<thinking>.*?</thinking>",
            "",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()

        # Remove markdown fences.
        text = re.sub(
            r"```json\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"```\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # Balanced-object extraction.
        start = text.find("{")

        while start >= 0:
            depth = 0
            in_string = False
            escaped = False

            for index in range(start, len(text)):
                char = text[index]

                if escaped:
                    escaped = False
                    continue

                if char == "\\" and in_string:
                    escaped = True
                    continue

                if char == '"':
                    in_string = not in_string
                    continue

                if in_string:
                    continue

                if char == "{":
                    depth += 1

                elif char == "}":
                    depth -= 1

                    if depth == 0:
                        candidate = text[start:index + 1]

                        try:
                            parsed = json.loads(candidate)
                            if isinstance(parsed, dict):
                                return parsed
                        except Exception:
                            pass

                        break

            start = text.find("{", start + 1)

        return None

    # ------------------------------------------------------------------
    # NORMALIZATION
    # ------------------------------------------------------------------

    def _normalize_result(
        self,
        parsed: dict[str, Any],
        facts: dict[str, Any],
        rules: list[Any],
        tables: list[dict[str, Any]],
    ) -> dict[str, Any]:

        constraints = parsed.get("constraints", [])
        unresolved = parsed.get("unresolved", [])

        if not isinstance(constraints, list):
            constraints = []

        if not isinstance(unresolved, list):
            unresolved = []

        normalized_constraints = []

        for item in constraints:
            if isinstance(item, str):
                normalized_constraints.append({
                    "id": self._slug(item),
                    "name": item,
                    "category": "Other",
                    "applicability": "applicable",
                    "status": "needs_calculation",
                    "value": None,
                    "unit": None,
                    "source_rules": [],
                    "source_tables": [],
                    "source_pdf_pages": [],
                    "regulation_references": [],
                    "required_inputs": [],
                    "calculation": None,
                    "reason": "",
                })
                continue

            if not isinstance(item, dict):
                continue

            applicability = str(
                item.get(
                    "applicability",
                    "applicable",
                )
            )

            if applicability not in {
                "applicable",
                "conditional",
                "not_applicable",
                "needs_information",
            }:
                applicability = "applicable"

            status = str(
                item.get(
                    "status",
                    "needs_calculation",
                )
            )

            if status not in {
                "resolved",
                "needs_calculation",
                "needs_verification",
            }:
                status = "needs_calculation"

            name = str(
                item.get("name", "") or ""
            )

            normalized_constraints.append({
                "id": str(
                    item.get(
                        "id",
                        self._slug(name),
                    ) or self._slug(name)
                ),
                "name": name,
                "category": str(
                    item.get(
                        "category",
                        "Other",
                    ) or "Other"
                ),
                "applicability": applicability,
                "status": status,
                "value": self._json_safe(
                    item.get("value")
                ),
                "unit": self._json_safe(
                    item.get("unit")
                ),
                "source_rules": self._list_or_empty(
                    item.get("source_rules")
                ),
                "source_tables": self._list_or_empty(
                    item.get("source_tables")
                ),
                "source_pdf_pages": self._list_or_empty(
                    item.get("source_pdf_pages")
                ),
                "regulation_references": self._list_or_empty(
                    item.get("regulation_references")
                ),
                "required_inputs": self._list_or_empty(
                    item.get("required_inputs")
                ),
                "calculation": self._json_safe(
                    item.get("calculation")
                ),
                "reason": str(
                    item.get("reason", "") or ""
                ),
            })

        # Do not call a non-empty discovery result "calculated".
        # Ollama discovers constraints; it does not perform deterministic
        # regulatory calculation here.
        if normalized_constraints:
            status = "resolved"
        else:
            status = "unresolved"

        return {
            "status": status,
            "model": self.model,
            "constraints": normalized_constraints,
            "unresolved": unresolved,
            "facts": facts,
            "rule_count": len(rules),
            "table_count": len(tables),
        }

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _slug(value: str) -> str:
        value = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            value.strip().lower(),
        )
        return value.strip("_") or "constraint"

    @staticmethod
    def _list_or_empty(value: Any) -> list[Any]:
        if value is None:
            return []

        if isinstance(value, list):
            return [
                ConstraintDiscovery._json_safe(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                ConstraintDiscovery._json_safe(item)
                for item in value
            ]

        return [
            ConstraintDiscovery._json_safe(value)
        ]


# ---------------------------------------------------------------------------
# BACKWARD COMPATIBILITY
# ---------------------------------------------------------------------------

ConstraintDiscoveryService = ConstraintDiscovery
