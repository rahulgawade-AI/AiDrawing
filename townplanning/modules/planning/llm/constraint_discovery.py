from __future__ import annotations

"""
Ollama-based UDCPR constraint discovery.

Architecture:

    Project Facts
          |
          +----------------------+
          |                      |
          v                      v
    PostgreSQL Rules       PostgreSQL Tables
          |                      |
          +----------+-----------+
                     |
                     v
              Chroma Semantic Search
                     |
                     v
                Gemma 3:12B
                     |
                     v
          Applicable Constraints

IMPORTANT
---------
The LLM does NOT determine what the project is.

Project facts are authoritative.

The LLM determines which supplied regulations are applicable
to the supplied project.

A regulation appearing in PostgreSQL, Chroma or the PDF does
NOT automatically become an applicable constraint.
"""

from dataclasses import dataclass, field
from typing import Any
import json
import re
from townplanning.ai.gpt_client import (
    GPTClient,
)

from townplanning.ai.models import (
    AIRequest,
)

DEFAULT_MODEL = "gemma3:12b"


# ============================================================================
# RESULT
# ============================================================================


@dataclass
class ConstraintDiscoveryResult:

    status: str

    model: str

    constraints: list[dict[str, Any]] = field(
        default_factory=list
    )

    unresolved: list[dict[str, Any]] = field(
        default_factory=list
    )

    facts: dict[str, Any] = field(
        default_factory=dict
    )

    rule_count: int = 0

    table_count: int = 0

    excluded_constraints: list[dict[str, Any]] = field(
        default_factory=list
    )

    missing_information: list[dict[str, Any]] = field(
        default_factory=list
    )

    retrieval: dict[str, Any] = field(
        default_factory=dict
    )

    raw_response: str = ""

    reason: str | None = None

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
            "excluded_constraints":
                self.excluded_constraints,
            "unresolved": self.unresolved,
            "missing_information":
                self.missing_information,
            "facts": self.facts,
            "rule_count": self.rule_count,
            "table_count": self.table_count,
            "retrieval": self.retrieval,
            "raw_response": self.raw_response,
            "reason": self.reason,
            "error": self.error,
        }


# ============================================================================
# SERVICE
# ============================================================================


class ConstraintDiscovery:

    DEFAULT_MODEL = DEFAULT_MODEL

    def __init__(
        self,
        ollama=None,
        rule_resolver=None,
        table_repository=None,
        pdf_repository=None,
        vector_search_service=None,
        chroma_retriever=None,
        model: str = DEFAULT_MODEL,
        max_rules: int = 150,
        max_tables: int = 60,
        chroma_top_k: int = 5,
        max_chroma_results: int = 50,
    ):

        self.ollama = ollama
        self.openai = GPTClient()

        self.rule_resolver = rule_resolver

        self.table_repository = (
            table_repository
        )

        self.pdf_repository = (
            pdf_repository
        )

        self.vector_search_service = (
            vector_search_service
        )

        # Backward-compatible name.
        self.chroma_retriever = (
            chroma_retriever
        )

        self.model = model

        self.max_rules = max_rules

        self.max_tables = max_tables

        self.chroma_top_k = chroma_top_k

        self.max_chroma_results = (
            max_chroma_results
        )

        if self.ollama is None:

            from townplanning.modules.planning.llm.ollama_client import (
                OllamaClient,
            )

            self.ollama = OllamaClient(
                model=model,
                timeout=600,
            )

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def discover(
        self,
        facts: Any = None,
        rules: list[Any] | None = None,
        pdf_evidence: list[Any] | None = None,
        max_rules: int | None = None,
        max_tables: int | None = None,
        project_context: Any = None,
        **kwargs: Any,
    ) -> ConstraintDiscoveryResult:

        if project_context is not None:
            facts = project_context

        if facts is None:
            facts = {}

        fact_values = self._facts_to_dict(
            facts
        )

        try:

            # ------------------------------------------------------------
            # RULES
            # ------------------------------------------------------------

            if rules is None:

                rules = self._load_rules(
                    facts,
                    max_rules
                    if max_rules is not None
                    else self.max_rules,
                )

            rules = list(
                rules or []
            )

            # ------------------------------------------------------------
            # TABLES
            # ------------------------------------------------------------

            tables = (
                self._load_relevant_tables(
                    facts=facts,
                    rules=rules,
                    max_tables=(
                        max_tables
                        if max_tables is not None
                        else self.max_tables
                    ),
                )
            )

            # ------------------------------------------------------------
            # CHROMA
            # ------------------------------------------------------------

            chroma_evidence = (
                self._retrieve_chroma_evidence(
                    facts=fact_values
                )
            )

            # ============================================================
            # PDF FALLBACK ONLY
            # ============================================================

            pdf_items = list(
                pdf_evidence or []
            )

            # Chroma is the primary regulatory evidence source.
            # PDF is used ONLY when Chroma returns no evidence.
            if not chroma_evidence:
                pdf_items = (
                    self._load_pdf_evidence(
                        facts
                    )
                )
            else:
                pdf_items = []

            # ------------------------------------------------------------
            # PROMPT
            # ------------------------------------------------------------
            constraint_evidence = (
    self._build_constraint_evidence(
        facts=fact_values,
        rules=rules,
        tables=tables,
        chroma_evidence=chroma_evidence,
    )
)

            prompt = self._build_prompt(
                facts=fact_values,
                rules=constraint_evidence[
                    "deterministic_rules"
                ],
                tables=constraint_evidence[
                    "tables"
            ],
                chroma_evidence=(
                    chroma_evidence
                ),
                pdf_evidence=pdf_items,
            )

            # ------------------------------------------------------------
            # OLLAMA
            # ------------------------------------------------------------
            print()
            print("=" * 100)
            print("FINAL PROMPT SENT TO OLLAMA")
            print("=" * 100)
            print(prompt)
            print("=" * 100)

            response = self.openai.generate(
                AIRequest(
                    system_prompt=(
                    "You are the regulatory constraint discovery "
                    "engine for an AI town-planning system. "
                    "Return ONLY valid JSON. "
                    "Use the supplied project facts and regulatory "
                    "evidence exactly as provided."
                ),
                user_prompt=prompt,
            )
        )

            raw = str(
                response.content
                if response.success
                else ""
            )

            print()
            print("=" * 100)
            print("RAW OLLAMA RESPONSE")
            print("=" * 100)
            print(raw)
            print("=" * 100)

            # ------------------------------------------------------------
            # PARSE
            # ------------------------------------------------------------

            parsed = self._parse_json(
                raw
            )
            ##########new ADDED

            
            ######### NEW ADDED

            # ------------------------------------------------------------
            # RETRY
            # ------------------------------------------------------------

            if parsed is None:

                retry_prompt = (
                    self._build_retry_prompt(
                        facts=fact_values,
                        rules=rules,
                        tables=tables,
                        chroma_evidence=(
                            chroma_evidence
                        ),
                        pdf_evidence=pdf_items,
                    )
                )

                retry_response = self.openai.generate(
                    AIRequest(
                    system_prompt=(
                    "You are the regulatory constraint discovery "
                    "engine for an AI town-planning system. "
                    "Return ONLY valid JSON."
                    ),
                user_prompt=retry_prompt,
                 )
                )

                retry_raw = str(
            retry_response.content
            if retry_response.success
                else ""
            )

                print()
                print("=" * 100)
                print(
                    "RAW OLLAMA RETRY RESPONSE"
                )
                print("=" * 100)
                print(retry_raw)
                print("=" * 100)

                parsed = (
                    self._parse_json(
                        retry_raw
                    )
                )

                if parsed is not None:
                    raw = retry_raw

            # ------------------------------------------------------------
            # INVALID RESPONSE
            # ------------------------------------------------------------

            if parsed is None:

                return ConstraintDiscoveryResult(
                    status="error",
                    model=self.model,
                    facts=fact_values,
                    rule_count=len(rules),
                    table_count=len(tables),
                    raw_response=raw,
                    retrieval={
                        "candidate_rule_count":
                            len(rules),

                        "table_count":
                            len(tables),

                        "chroma_count":
                            len(
                                chroma_evidence
                            ),

                        "pdf_page_count":
                            len(pdf_items),
                    },
                    unresolved=[
                        {
                            "reason":
                                "Ollama returned invalid JSON"
                        }
                    ],
                    reason=(
                        "Ollama returned invalid JSON"
                    ),
                    error=(
                        "Ollama returned invalid JSON"
                    ),
                )

            # ------------------------------------------------------------
            # NORMALIZE
            # ------------------------------------------------------------

            normalized = (
                self._normalize_result(
                    parsed=parsed,
                    facts=fact_values,
                    rules=rules,
                    tables=tables,
                    raw_response=raw,
                )
            )

            normalized[
                "retrieval"
            ] = {
                "candidate_rule_count":
                    len(rules),

                "table_count":
                    len(tables),

                "chroma_count":
                    len(
                        chroma_evidence
                    ),

                "pdf_page_count":
                    len(pdf_items),
            }

            return ConstraintDiscoveryResult(
                status=normalized[
                    "status"
                ],

                model=self.model,

                constraints=normalized[
                    "constraints"
                ],

                unresolved=normalized[
                    "unresolved"
                ],

                facts=fact_values,

                rule_count=len(rules),

                table_count=len(tables),

                excluded_constraints=normalized.get(
                    "excluded_constraints",
                    [],
                ),

                missing_information=normalized.get(
                    "missing_information",
                    [],
                ),

                retrieval=normalized[
                    "retrieval"
                ],

                raw_response=raw,

                reason=normalized.get(
                    "reason"
                ),

                error=normalized.get(
                    "error"
                ),
            )

        except Exception as exc:

            return ConstraintDiscoveryResult(
                status="error",

                model=self.model,

                constraints=[],

                unresolved=[
                    {
                        "reason": str(exc)
                    }
                ],

                facts=fact_values,

                rule_count=len(
                    rules or []
                ),

                table_count=0,

                raw_response="",

                reason=str(exc),

                error=str(exc),
            )

    # ========================================================================
    # FACTS
    # ========================================================================

    @staticmethod
    def _facts_to_dict(
        facts: Any,
    ) -> dict[str, Any]:

        if facts is None:
            return {}

        if isinstance(
            facts,
            dict,
        ):
            return dict(facts)

        if hasattr(
            facts,
            "to_dict",
        ):

            try:

                value = (
                    facts.to_dict()
                )

                if isinstance(
                    value,
                    dict,
                ):
                    return dict(
                        value
                    )

            except Exception:
                pass

        if hasattr(
            facts,
            "__dict__",
        ):

            return {
                key:
                    ConstraintDiscovery._json_safe(
                        value
                    )

                for key, value
                in vars(facts).items()

                if not key.startswith("_")
            }

        try:
            return dict(facts)

        except Exception:

            return {
                "value": str(facts)
            }

    # ========================================================================
    # RULES
    # ========================================================================

    def _load_rules(
        self,
        facts: Any,
        max_rules: int,
    ) -> list[Any]:

        if self.rule_resolver is None:
            return []

        try:

            if hasattr(
                self.rule_resolver,
                "resolve_building_rules",
            ):

                result = (
                    self.rule_resolver
                    .resolve_building_rules(
                        facts
                    )
                )

            elif hasattr(
                self.rule_resolver,
                "resolve",
            ):

                result = (
                    self.rule_resolver
                    .resolve(
                        facts
                    )
                )

            else:
                return []

            return list(
                result or []
            )[:max_rules]

        except Exception:

            return []

    # ========================================================================
    # TABLES
    # ========================================================================

    def _load_relevant_tables(
        self,
        facts: Any,
        rules: list[Any],
        max_tables: int,
    ) -> list[dict[str, Any]]:

        if self.table_repository is None:
            return []

        try:

            if hasattr(
                self.table_repository,
                "list",
            ):

                raw_tables = (
                    self.table_repository
                    .list()
                )

            elif hasattr(
                self.table_repository,
                "get_all",
            ):

                raw_tables = (
                    self.table_repository
                    .get_all()
                )

            else:
                raw_tables = []

            fact_text = json.dumps(
                self._json_safe(
                    self._facts_to_dict(
                        facts
                    )
                ),
                ensure_ascii=False,
                default=str,
            ).lower()

            rules_text = json.dumps(
                self._json_safe(
                    rules
                ),
                ensure_ascii=False,
                default=str,
            ).lower()

            searchable_context = (
                fact_text
                + " "
                + rules_text
            )

            keywords = [
                "fsi",
                "tdr",
                "premium",
                "incentive",
                "setback",
                "margin",
                "height",
                "floor",
                "storey",
                "coverage",
                "open space",
                "amenity",
                "parking",
                "fire",
                "lift",
                "stair",
                "staircase",
                "exit",
                "accessibility",
                "ramp",
                "light",
                "ventilation",
                "sanitation",
                "water closet",
                "urinal",
                "basement",
                "plinth",
                "road",
                "reservation",
                "residential",
                "bungalow",
                "villa",
                "hotel",
                "hospital",
                "restaurant",
                "school",
                "hostel",
                "commercial",
                "industrial",
                "institutional",
            ]

            scored = []

            for table in (
                raw_tables or []
            ):

                if isinstance(
                    table,
                    dict,
                ):

                    title = str(
                        table.get(
                            "title",
                            table.get(
                                "name",
                                "",
                            ),
                        )
                        or ""
                    )

                    table_id = str(
                        table.get(
                            "id",
                            table.get(
                                "table_id",
                                "",
                            ),
                        )
                        or ""
                    )

                    page = table.get(
                        "page"
                    )

                    headers = (
                        table.get(
                            "headers",
                            [],
                        )
                        or []
                    )

                    rows = (
                        table.get(
                            "rows",
                            [],
                        )
                        or []
                    )

                else:

                    title = str(
                        getattr(
                            table,
                            "title",
                            "",
                        )
                        or ""
                    )

                    table_id = str(
                        getattr(
                            table,
                            "id",
                            "",
                        )
                        or ""
                    )

                    page = getattr(
                        table,
                        "page",
                        None,
                    )

                    headers = (
                        getattr(
                            table,
                            "headers",
                            [],
                        )
                        or []
                    )

                    rows = (
                        getattr(
                            table,
                            "rows",
                            [],
                        )
                        or []
                    )

                headers = [
                    self._json_safe(
                        x
                    )
                    for x in headers
                ]

                rows = self._safe_rows(
                    rows
                )

                searchable = (
                    title
                    + " "
                    + json.dumps(
                        headers,
                        default=str,
                    )
                    + " "
                    + json.dumps(
                        rows,
                        default=str,
                    )
                ).lower()

                score = 0

                for keyword in keywords:

                    if keyword in searchable:
                        score += 2

                    if keyword in searchable_context:
                        score += 1

                # Strong general regulatory tables.
                for marker in (
                    "fsi",
                    "parking",
                    "fire",
                    "setback",
                    "height",
                    "residential",
                ):

                    if marker in searchable:
                        score += 10

                if score <= 0:
                    continue

                scored.append(
                    {
                        "id": table_id,
                        "title": title,
                        "page": self._json_safe(
                            page
                        ),
                        "headers": headers,
                        "rows": rows,
                        "_score": score,
                    }
                )

            scored.sort(
                key=lambda x:
                    x.get(
                        "_score",
                        0,
                    ),
                reverse=True,
            )

            result = []

            for item in scored[
                :max_tables
            ]:

                clean = dict(
                    item
                )

                clean.pop(
                    "_score",
                    None,
                )

                result.append(
                    clean
                )

            return result

        except Exception:

            return []

    # ========================================================================
    # CHROMA
    # ========================================================================

    def _retrieve_chroma_evidence(
        self,
        facts: dict[str, Any],
    ) -> list[dict[str, Any]]:

        service = (
            self.vector_search_service
        )

        if service is None:
            service = (
                self.chroma_retriever
            )

        if service is None:
            return []

        location = self._first_value(
            facts,
            [
                "location",
                "locality",
                "city",
                "district",
            ],
        )

        city = self._first_value(
            facts,
            [
                "city",
            ],
        )

        authority = self._first_value(
            facts,
            [
                "planning_authority",
                "municipality",
                "development_authority",
            ],
        )

        building_type = self._first_value(
            facts,
            [
                "building_type",
                "project_type",
            ],
        )

        building_use = self._first_value(
            facts,
            [
                "building_use",
            ],
        )

        plot_area = self._first_value(
            facts,
            [
                "plot_area",
            ],
        )

        road_width = self._first_value(
            facts,
            [
                "road_width",
            ],
        )

        base = " ".join(
            str(x)
            for x in (
                location,
                city,
                authority,
                building_type,
                building_use,
                f"plot area {plot_area} square metres"
                if plot_area is not None
                else "",
                f"road width {road_width} metres"
                if road_width is not None
                else "",
            )
            if x
        )

        categories = [

            "FSI basic maximum permissible "
            "premium incentive TDR additional FSI",

            "setbacks margins front rear side "
            "building line road width",

            "building height floors storeys "
            "floor height",

            "ground coverage built up area "
            "building footprint",

            "fire safety fire access fire staircase "
            "fire lift emergency exit refuge area",

            "lift requirements elevator lift room "
            "staircase",

            "staircase width corridor width "
            "exit width emergency exit",

            "parking car parking two wheeler "
            "visitor parking parking dimensions",

            "accessibility barrier free ramp "
            "accessible entrance",

            "light ventilation natural light "
            "natural ventilation duct shaft",

            "open space recreation amenity "
            "common open space",

            "sanitation water closet toilet "
            "urinal bathroom water supply drainage",

            "basement podium stilt plinth "
            "terrace balcony",

            "building separation distance",

            "road widening reservation "
            "development plan road",

        ]

        all_results: dict[
            str,
            dict[str, Any]
        ] = {}

        for category in categories:

            query = (
                base
                + " "
                + category
            ).strip()

            try:

                results = self._search_semantic(
                    service,
                    query,
                )

            except Exception:

                continue

            for result in (
                results or []
            ):

                item = (
                    self._search_result_to_dict(
                        result
                    )
                )

                if not item:
                    continue

                result_id = str(
                    item.get(
                        "id",
                        "",
                    )
                )

                if not result_id:

                    result_id = (
                        self._slug(
                            item.get(
                                "text",
                                "",
                            )[:200]
                        )
                    )

                    item[
                        "id"
                    ] = result_id

                # Keep the strongest result.
                previous = (
                    all_results.get(
                        result_id
                    )
                )

                if (
                    previous is None
                    or float(
                        item.get(
                            "score",
                            0,
                        )
                        or 0
                    )
                    > float(
                        previous.get(
                            "score",
                            0,
                        )
                        or 0
                    )
                ):

                    all_results[
                        result_id
                    ] = item

        results = list(
            all_results.values()
        )

        results.sort(
            key=lambda x:
                float(
                    x.get(
                        "score",
                        0,
                    )
                    or 0
                ),
            reverse=True,
        )

        return results[
            :self.max_chroma_results
        ]

    def _search_semantic(
        self,
        service: Any,
        query: str,
    ) -> list[Any]:

        # Current SemanticSearchService versions
        # support search(query, top_k).
        try:

            return list(
                service.search(
                    query,
                    top_k=self.chroma_top_k,
                )
                or []
            )

        except TypeError:

            # Older implementation:
            # search(query)
            return list(
                service.search(
                    query
                )
                or []
            )

    @staticmethod
    def _search_result_to_dict(
        result: Any,
    ) -> dict[str, Any]:

        if result is None:
            return {}

        if isinstance(
            result,
            dict,
        ):

            return {
                "id": str(
                    result.get(
                        "id",
                        "",
                    )
                    or ""
                ),

                "text": str(
                    result.get(
                        "text",
                        result.get(
                            "document",
                            "",
                        ),
                    )
                    or ""
                ),

                "score": float(
                    result.get(
                        "score",
                        0,
                    )
                    or 0
                ),

                "metadata":
                    ConstraintDiscovery._json_safe(
                        result.get(
                            "metadata",
                            {},
                        )
                    ),
            }

        return {
            "id": str(
                getattr(
                    result,
                    "id",
                    "",
                )
                or ""
            ),

            "text": str(
                getattr(
                    result,
                    "text",
                    "",
                )
                or ""
            ),

            "score": float(
                getattr(
                    result,
                    "score",
                    0,
                )
                or 0
            ),

            "metadata":
                ConstraintDiscovery._json_safe(
                    getattr(
                        result,
                        "metadata",
                        {},
                    )
                ),
        }

    # ========================================================================
    # PDF
    # ========================================================================

    def _load_pdf_evidence(
        self,
        facts: Any,
    ) -> list[Any]:

        if self.pdf_repository is None:
            return []

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

            if not callable(method):
                continue

            try:

                result = method(
                    facts
                )

                if result is None:
                    return []

                if isinstance(
                    result,
                    list,
                ):
                    return result

                return [
                    result
                ]

            except Exception:
                continue

        return []

    # ========================================================================
    # PROMPT
    # ========================================================================

    def _build_prompt(
        self,
        facts: dict[str, Any],
        rules: list[Any],
        tables: list[dict[str, Any]],
        chroma_evidence: list[dict[str, Any]],
        pdf_evidence: list[Any],
    ) -> str:

        project_json = json.dumps(
            self._json_safe(
                facts
            ),
            indent=2,
            ensure_ascii=False,
            default=str,
        )

        rules_json = json.dumps(
            self._json_safe(
                rules
            ),
            indent=2,
            ensure_ascii=False,
            default=str,
        )

        tables_json = json.dumps(
            self._json_safe(
                tables
            ),
            indent=2,
            ensure_ascii=False,
            default=str,
        )

        chroma_json = json.dumps(
            self._json_safe(
                chroma_evidence
            ),
            indent=2,
            ensure_ascii=False,
            default=str,
        )

        pdf_json = json.dumps(
            self._json_safe(
                pdf_evidence
            ),
            indent=2,
            ensure_ascii=False,
            default=str,
        )

        template = r"""
You are the Regulatory Constraint Discovery Engine for an
AI Town Planning Platform.

MODEL:
Gemma 3:12B

Your task is to identify the regulatory constraints that
apply to THE CURRENT PROJECT.

You are NOT designing the building.

You are NOT calculating a final building design.

You MUST NOT change or reinterpret the project facts.

============================================================
AUTHORITATIVE PROJECT FACTS
============================================================

The following project facts are authoritative.

PROJECT FACTS:

__PROJECT_FACTS__

IMPORTANT:

Never change:

- location
- locality
- city
- district
- state
- planning authority
- municipality
- plot area
- plot number
- road width
- building use
- building type
- occupancy
- number of units
- unit mix
- project classification

If a field is supplied, use it as supplied.

Do NOT classify the project yourself.

============================================================
PROJECT TYPE
============================================================

The system supports:

- residential apartment
- bungalow
- villa
- row house
- hotel
- hospital
- nursing home
- restaurant
- school
- college
- hostel
- commercial
- office
- shop
- industrial
- warehouse
- institutional
- religious
- assembly
- mixed use
- parking building
- other special buildings

The CURRENT PROJECT FACTS determine which one applies.

A regulation appearing in the evidence does NOT automatically
apply to the project.

============================================================
JURISDICTION / LOCATION
============================================================

Location is extremely important.

Regulations may depend on:

- state
- district
- city
- municipal corporation
- planning authority
- development authority
- locality
- special planning area
- congested/non-congested area
- zone
- road width
- reservation

Use the supplied location and authority.

If the project is in a locality such as:

Shivajinagar
Hadapsar
Kothrud
Baner
Aundh
Kharadi
Viman Nagar
Wakad

do NOT assume another locality.

Do NOT substitute a different authority.

Do NOT invent locality-specific rules.

============================================================
POSTGRESQL UDCPR RULES
============================================================

These are deterministic regulatory candidates from PostgreSQL.
Each rule includes a deterministic evaluation status.

IMPORTANT:

The deterministic status is authoritative.

Rules with status "applicable":
- Treat them as applicable to the current project.
- Do NOT override them as not_applicable.
- Preserve them as regulatory constraints when relevant.

Rules with status "unresolved":
- Treat them as potentially applicable.
- Do NOT discard them.
- Return them as conditional / needs_information when required facts are missing.
- List the missing facts in required_inputs.

Rules with status "not_applicable":
- Do NOT return them as constraints.
- Do NOT reinterpret them as applicable.

Rules with status "unconditional":
- Treat them as applicable unless supplied evidence establishes that they do not apply.

Rules with status "interactive":
- Treat them as conditional.
- Identify the confirmation/input required.

The deterministic status comes from the rule evaluation engine
and MUST NOT be recomputed by the model.

============================================================
DETERMINISTIC RULE HANDLING
============================================================

The deterministic rule evaluation has already been performed
by the planning rule engine.

DO NOT re-evaluate deterministic applicability.

For every rule with:

status = "applicable"

you MUST preserve that rule as a constraint in the output.

Do NOT omit an applicable deterministic rule merely because:

- it appears administrative
- it appears general
- it does not contain a numeric value
- you consider it less important
- another rule appears similar

If multiple applicable rules describe the same regulatory
requirement, they may be consolidated into ONE constraint,
but ALL source rule IDs must be preserved in source_rules.

For every rule with:

status = "unresolved"

do NOT discard it automatically.

If the rule represents a potentially applicable requirement,
return it as:

applicability = "conditional"

and:

status = "needs_information"

with the missing facts listed in required_inputs.

For every rule with:

status = "not_applicable"

do NOT return it.

For every rule with:

status = "unconditional"

treat it as applicable unless the evidence explicitly shows
that it does not apply.

For every rule with:

status = "interactive"

return it as conditional and identify the required
confirmation/input.

The deterministic status is authoritative.

============================================================
AUTHORITATIVE PROJECT FACT OUTPUT
============================================================

The project object in the final JSON is NOT an opportunity
to classify or reinterpret the project.

Copy the following authoritative project facts exactly
from PROJECT FACTS:

- building_type
- building_use
- occupancy
- project classification
- location
- locality
- city
- district
- state
- planning authority
- municipality

If a value is supplied, reproduce that value.

NEVER change:

- residential to mixed-use
- mixed-use to residential
- residential apartment to hotel
- residential apartment to hostel
- residential apartment to commercial
- one planning authority to another
- one locality to another

If mixed_use is false or the supplied project facts identify
a residential-only project, do NOT create mixed-use
requirements unless the supplied evidence explicitly
establishes a mixed-use component.

The "project" object must reflect the supplied facts,
not the model's interpretation.

============================================================
MANDATORY APPLICABLE RULE COVERAGE
============================================================

Every deterministic rule whose status is "applicable"
MUST be represented in the final constraints unless
it is consolidated with another applicable rule describing
the same requirement.

When consolidating rules, preserve ALL contributing rule IDs
in source_rules.

Do NOT reduce the applicable rule set to only the rules
that contain numeric values.

Do NOT select only the most important or most obvious rules.

Do NOT omit administrative, procedural, safety, access,
infrastructure, parking, fire, sanitation, accessibility,
or other applicable requirements merely because they are
not design calculations.

The deterministic rule engine has already established
applicability. The model's responsibility is to transform
those applicable rules into the required output structure
while preserving traceability.

__RULES__

============================================================
POSTGRESQL UDCPR TABLES
============================================================

Use these tables when the rule refers to a table.

__TABLES__

============================================================
CHROMA SEMANTIC EVIDENCE
============================================================

The following evidence was retrieved from the existing
Chroma regulatory knowledge base.

Use it to locate relevant regulations, clauses and tables.

Do NOT treat semantic similarity as proof of applicability.

__CHROMA_EVIDENCE__

============================================================
PDF EVIDENCE
============================================================

__PDF_EVIDENCE__

============================================================
APPLICABILITY
============================================================

For EACH candidate constraint ask:

Does this regulation actually apply to THIS project?

A regulation is applicable only when the supplied project facts
and supplied regulatory evidence support applicability.

Do NOT include a regulation merely because:

- it appears in a table
- it appears in Chroma
- it appears in the PDF
- it contains a matching keyword
- it is common planning practice

============================================================
BUILDING USE SPECIFIC RULES
============================================================

Residential apartment:

Do NOT include hotel requirements.

Do NOT include hospital requirements.

Do NOT include restaurant requirements.

Do NOT include school requirements.

Do NOT include industrial requirements.

Do NOT include institutional requirements.

Do NOT include hostel requirements.

UNLESS the supplied evidence explicitly states that the
requirement applies to residential buildings.

Hotel:

Include hotel requirements when supported.

Hospital:

Include hospital requirements when supported.

Restaurant:

Include restaurant requirements when supported.

School / educational:

Include educational requirements when supported.

Bungalow / villa:

Include bungalow/villa requirements when supported.

Hostel:

Include hostel requirements when supported.

Mixed-use:

Evaluate each actual use component separately.

Example:

Residential + Commercial

may require:

- residential requirements
- commercial requirements
- common site requirements
- mixed-use requirements

============================================================
REGULATORY CATEGORIES
============================================================

Consider ALL categories supported by the evidence.

Do not focus only on parking.

Potential categories include:

Land use / zoning
Plot eligibility
Plot area
Plot dimensions
Road width
Road frontage
Road widening
DP reservation
Reservation
FSI
Basic FSI
Maximum FSI
Premium FSI
TDR
Incentive FSI
Additional FSI
FSI exclusions
FSI deductions
Ground coverage
Built-up area
Setbacks
Margins
Front setback
Rear setback
Side setback
Building line
Building height
Number of floors
Storeys
Floor height
Building footprint
Open space
Recreational open space
Amenity space
Parking
Car parking
Two-wheeler parking
Visitor parking
Loading/unloading
Fire safety
Fire access
Fire staircase
Fire lift
Emergency exits
Exit width
Staircase
Staircase width
Corridor
Corridor width
Lift
Lift requirements
Accessibility
Barrier-free access
Ramp
Light
Natural lighting
Ventilation
Natural ventilation
Duct
Shaft
Sanitation
Water closets
Urinals
Bathrooms
Water supply
Drainage
Basement
Podium
Stilt
Plinth
Terrace
Balcony
Refuge area
Building separation
Service areas
Utilities
Special building requirements
Use-specific requirements

This list is NOT exhaustive.

============================================================
CONDITIONAL REQUIREMENTS
============================================================

If a requirement depends on information not currently supplied,
do NOT discard it.

Return it as conditional / needs_information.

Examples:

Fire lift
Fire staircase
Refuge area
Building height
Number of exits
Lift requirements
Parking
Accessibility

Use:

"applicability": "conditional"

and/or:

"status": "needs_information"

and specify:

"required_inputs": [...]

Do NOT claim a numeric requirement when the supplied evidence
does not establish it.

============================================================
NO INVENTED VALUES
============================================================

Never invent:

FSI
setbacks
parking counts
parking dimensions
height
coverage
fire requirements
lift requirements
staircase dimensions
sanitation requirements
open-space requirements
amenity requirements

If the evidence does not establish the value:

"value": null

and explain why.

============================================================
SOURCE TRACEABILITY
============================================================

Every constraint should preserve source information when available.

Use:

source_rules
source_tables
source_pdf_pages
regulation_references

Never invent source IDs.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

No markdown.

No code fences.

No explanation.

No <think>.

Use exactly this structure:

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
      "name": "Human readable name",
      "category": "category",
      "applicability": "applicable",
      "status": "resolved",
      "reason": "Why it applies",
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
      "reason": "..."
    }
  ],
  "missing_information": [
    {
      "field": "...",
      "reason": "..."
    }
  ]
}

Allowed applicability:

applicable
conditional
not_applicable
needs_information

Allowed status:

resolved
needs_calculation
needs_verification

============================================================
FINAL CHECK
============================================================

Before returning JSON:

1. Read the project facts.

2. Identify the supplied location and authority.

3. Do NOT change the location.

4. Identify the actual building use.

5. Identify the actual building type.

6. Identify occupancy.

7. Identify mixed-use components.

8. Examine PostgreSQL rules.

9. Examine PostgreSQL tables.

10. Examine Chroma evidence.

11. Examine PDF evidence.

12. Determine applicability.

13. Exclude unrelated building-use-specific rules.

14. Keep conditional rules.

15. Keep rules requiring missing information.

16. Preserve source traceability.

17. Never invent numeric values.

18. Return JSON only.

Now determine the complete regulatory constraint set for
THE CURRENT PROJECT.

__END__
"""

        return (
            template
            .replace(
                "__PROJECT_FACTS__",
                project_json,
            )
            .replace(
                "__RULES__",
                rules_json,
            )
            .replace(
                "__TABLES__",
                tables_json,
            )
            .replace(
                "__CHROMA_EVIDENCE__",
                chroma_json,
            )
            .replace(
                "__PDF_EVIDENCE__",
                pdf_json,
            )
        )

    # ========================================================================
    # RETRY
    # ========================================================================

    def _build_retry_prompt(
        self,
        facts: dict[str, Any],
        rules: list[Any],
        tables: list[dict[str, Any]],
        chroma_evidence: list[dict[str, Any]],
        pdf_evidence: list[Any],
    ) -> str:

        return (
            "Return ONLY valid JSON.\n"
            "No markdown.\n"
            "No explanation.\n"
            "No <think>.\n\n"
            "The project facts are authoritative. "
            "Do not change the project type, location, "
            "authority or building use.\n\n"
            "PROJECT FACTS:\n"
            + json.dumps(
                self._json_safe(
                    facts
                ),
                indent=2,
                ensure_ascii=False,
                default=str,
            )
            + "\n\nPOSTGRES RULES:\n"
            + json.dumps(
                self._json_safe(
                    rules
                ),
                indent=2,
                ensure_ascii=False,
                default=str,
            )
            + "\n\nPOSTGRES TABLES:\n"
            + json.dumps(
                self._json_safe(
                    tables
                ),
                indent=2,
                ensure_ascii=False,
                default=str,
            )
            + "\n\nCHROMA EVIDENCE:\n"
            + json.dumps(
                self._json_safe(
                    chroma_evidence
                ),
                indent=2,
                ensure_ascii=False,
                default=str,
            )
            + "\n\nPDF EVIDENCE:\n"
            + json.dumps(
                self._json_safe(
                    pdf_evidence
                ),
                indent=2,
                ensure_ascii=False,
                default=str,
            )
            + """

Return:

{
  "status": "resolved",
  "project": {
    "building_type": "...",
    "building_use": "...",
    "occupancy": "..."
  },
  "constraints": [],
  "excluded_constraints": [],
  "missing_information": []
}
"""
        )

    # ========================================================================
    # JSON PARSER
    # ========================================================================

    @staticmethod
    def _parse_json(
        raw: Any,
    ) -> dict[str, Any] | None:

        if raw is None:
            return None

        if isinstance(
            raw,
            dict,
        ):
            return raw

        text = str(
            raw
        ).strip()

        if not text:
            return None

        text = re.sub(
            r"<think>.*?</think>",
            "",
            text,
            flags=re.I | re.S,
        ).strip()

        text = re.sub(
            r"<thinking>.*?</thinking>",
            "",
            text,
            flags=re.I | re.S,
        ).strip()

        text = re.sub(
            r"```json\s*",
            "",
            text,
            flags=re.I,
        )

        text = re.sub(
            r"```\s*",
            "",
            text,
            flags=re.I,
        ).strip()

        try:

            value = json.loads(
                text
            )

            if isinstance(
                value,
                dict,
            ):
                return value

        except Exception:
            pass

        # ------------------------------------------------------------
        # Balanced JSON object extraction.
        # ------------------------------------------------------------

        start = text.find(
            "{"
        )

        while start >= 0:

            depth = 0

            in_string = False

            escaped = False

            for index in range(
                start,
                len(text),
            ):

                char = text[
                    index
                ]

                if escaped:

                    escaped = False

                    continue

                if (
                    char == "\\"
                    and in_string
                ):

                    escaped = True

                    continue

                if char == '"':

                    in_string = (
                        not in_string
                    )

                    continue

                if in_string:
                    continue

                if char == "{":

                    depth += 1

                elif char == "}":

                    depth -= 1

                    if depth == 0:

                        candidate = (
                            text[
                                start:
                                index + 1
                            ]
                        )

                        try:

                            value = (
                                json.loads(
                                    candidate
                                )
                            )

                            if isinstance(
                                value,
                                dict,
                            ):
                                return value

                        except Exception:
                            pass

                        break

            start = text.find(
                "{",
                start + 1,
            )

        return None

    # ========================================================================
    # NORMALIZATION
    # ========================================================================

    def _normalize_result(
        self,
        parsed: dict[str, Any],
        facts: dict[str, Any],
        rules: list[Any],
        tables: list[dict[str, Any]],
        raw_response: str,
    ) -> dict[str, Any]:

        constraints = parsed.get(
            "constraints",
            [],
        )

        if not isinstance(
            constraints,
            list,
        ):
            constraints = []

        unresolved = parsed.get(
            "unresolved",
            [],
        )

        if not isinstance(
            unresolved,
            list,
        ):
            unresolved = []

        excluded = parsed.get(
            "excluded_constraints",
            [],
        )

        if not isinstance(
            excluded,
            list,
        ):
            excluded = []

        missing = parsed.get(
            "missing_information",
            [],
        )

        if not isinstance(
            missing,
            list,
        ):
            missing = []

        normalized = []

        for item in constraints:

            if isinstance(
                item,
                str,
            ):

                normalized.append(
                    {
                        "id": self._slug(
                            item
                        ),

                        "name": item,

                        "category": "Other",

                        "applicability":
                            "applicable",

                        "status":
                            "needs_calculation",

                        "value": None,

                        "unit": None,

                        "source_rules": [],

                        "source_tables": [],

                        "source_pdf_pages": [],

                        "regulation_references": [],

                        "required_inputs": [],

                        "calculation": None,

                        "reason": "",
                    }
                )

                continue

            if not isinstance(
                item,
                dict,
            ):
                continue

            name = str(
                item.get(
                    "name",
                    "",
                )
                or ""
            )

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

                applicability = (
                    "applicable"
                )

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

                status = (
                    "needs_calculation"
                )

            normalized.append(
                {
                    "id": str(
                        item.get(
                            "id",
                            self._slug(
                                name
                            ),
                        )
                        or self._slug(
                            name
                        )
                    ),

                    "name": name,

                    "category": str(
                        item.get(
                            "category",
                            "Other",
                        )
                        or "Other"
                    ),

                    "applicability":
                        applicability,

                    "status":
                        status,

                    "value":
                        self._json_safe(
                            item.get(
                                "value"
                            )
                        ),

                    "unit":
                        self._json_safe(
                            item.get(
                                "unit"
                            )
                        ),

                    "source_rules":
                        self._list_or_empty(
                            item.get(
                                "source_rules"
                            )
                        ),

                    "source_tables":
                        self._list_or_empty(
                            item.get(
                                "source_tables"
                            )
                        ),

                    "source_pdf_pages":
                        self._list_or_empty(
                            item.get(
                                "source_pdf_pages"
                            )
                        ),

                    "regulation_references":
                        self._list_or_empty(
                            item.get(
                                "regulation_references"
                            )
                        ),

                    "required_inputs":
                        self._list_or_empty(
                            item.get(
                                "required_inputs"
                            )
                        ),

                    "calculation":
                        self._json_safe(
                            item.get(
                                "calculation"
                            )
                        ),

                    "reason": str(
                        item.get(
                            "reason",
                            "",
                        )
                        or ""
                    ),
                }
            )

            

        return {
            "status": (
                "resolved"
                if normalized
                else "unresolved"
            ),

            "model": self.model,

            "constraints":
                normalized,

            "unresolved":
                unresolved,

            "excluded_constraints":
                [
                    self._json_safe(
                        x
                    )
                    for x in excluded
                ],

            "missing_information":
                [
                    self._json_safe(
                        x
                    )
                    for x in missing
                ],

            "facts":
                facts,

            "rule_count":
                len(rules),

            "table_count":
                len(tables),

            "reason":
                None,

            "error":
                None,
        }

    # ========================================================================
    # HELPERS
    # ========================================================================

    @staticmethod
    def _first_value(
        facts: dict[str, Any],
        names: list[str],
    ) -> Any:

        for name in names:

            value = facts.get(
                name
            )

            if (
                value is not None
                and value != ""
            ):
                return value

        return None

    @staticmethod
    def _slug(
        value: str,
    ) -> str:

        value = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            str(
                value
            ).strip().lower(),
        )

        return (
            value.strip("_")
            or "constraint"
        )

    @staticmethod
    def _list_or_empty(
        value: Any,
    ) -> list[Any]:

        if value is None:
            return []

        if isinstance(
            value,
            list,
        ):

            return [
                ConstraintDiscovery._json_safe(
                    x
                )
                for x in value
            ]

        if isinstance(
            value,
            tuple,
        ):

            return [
                ConstraintDiscovery._json_safe(
                    x
                )
                for x in value
            ]

        return [
            ConstraintDiscovery._json_safe(
                value
            )
        ]

    @staticmethod
    def _safe_rows(
        rows: Any,
    ) -> list[Any]:

        if not isinstance(
            rows,
            (list, tuple),
        ):
            return []

        result = []

        for row in rows:

            if isinstance(
                row,
                dict,
            ):

                result.append(
                    {
                        str(k):
                            ConstraintDiscovery._json_safe(
                                v
                            )

                        for k, v
                        in row.items()
                    }
                )

            elif isinstance(
                row,
                (list, tuple),
            ):

                result.append(
                    [
                        ConstraintDiscovery._json_safe(
                            x
                        )
                        for x in row
                    ]
                )

            else:

                result.append(
                    ConstraintDiscovery._json_safe(
                        row
                    )
                )

        return result

    @staticmethod
    def _json_safe(
        value: Any,
    ) -> Any:

        if value is None:
            return None

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        if isinstance(
            value,
            dict,
        ):

            return {
                str(k):
                    ConstraintDiscovery._json_safe(
                        v
                    )

                for k, v
                in value.items()
            }

        if isinstance(
            value,
            (list, tuple),
        ):

            return [
                ConstraintDiscovery._json_safe(
                    x
                )
                for x in value
            ]

        return str(
            value
        )
    

    def _build_constraint_evidence(
        self,
        facts: dict[str, Any],
        rules: list[Any],
        tables: list[dict[str, Any]],
        chroma_evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build a compact regulatory evidence package.

    Do not send hundreds of unrelated rules/tables to Gemma.

    Evidence is grouped by regulatory category.
    """

        categories = {
            "fsi": [
            "fsi",
            "tdr",
            "premium",
            "incentive",
            "floor space",
        ],

            "setbacks": [
            "setback",
            "margin",
            "building line",
            "front margin",
            "rear margin",
            "side margin",
        ],

        "height": [
            "height",
            "storey",
            "storeys",
            "floor",
        ],

        "coverage": [
            "coverage",
            "built-up",
            "footprint",
        ],

        "parking": [
            "parking",
            "car parking",
            "two wheeler",
            "visitor parking",
        ],

        "fire": [
            "fire",
            "fire safety",
            "fire protection",
            "fire lift",
            "fire staircase",
            "refuge",
            "emergency exit",
        ],

        "lift": [
            "lift",
            "elevator",
            "lift room",
        ],

        "staircase": [
            "stair",
            "staircase",
            "exit",
            "corridor",
        ],

        "accessibility": [
            "accessibility",
            "barrier free",
            "ramp",
            "accessible",
        ],

        "light_ventilation": [
            "light",
            "ventilation",
            "natural light",
            "natural ventilation",
            "duct",
            "shaft",
        ],

        "open_space": [
            "open space",
            "recreation",
            "amenity",
            "common open space",
        ],

        "sanitation": [
            "sanitation",
            "toilet",
            "water closet",
            "urinal",
            "bathroom",
            "drainage",
        ],

        "basement_plinth": [
            "basement",
            "podium",
            "stilt",
            "plinth",
            "terrace",
            "balcony",
        ],

        "road_access": [
            "road",
            "road width",
            "road widening",
            "access",
            "entrance",
            "exit",
        ],

        "reservation": [
            "reservation",
            "road widening",
            "development plan",
            "dp reservation",
        ],

        "building_separation": [
            "building separation",
            "separation distance",
            "distance between buildings",
        ],
    }

        result = {}

        # ------------------------------------------------------------
        # CHROMA
        # ------------------------------------------------------------

        for category, terms in categories.items():

            matches = []

            for item in chroma_evidence or []:

                text = str(
                    item.get(
                        "text",
                        "",
                    )
                    or ""
                ).lower()

                metadata = str(
                    item.get(
                        "metadata",
                        {},
                    )
                    or ""
                ).lower()

                searchable = (
                    text
                    + " "
                    + metadata
                )

                if any(
                    term in searchable
                    for term in terms
                ):

                    matches.append(
                        {
                        "id": item.get(
                            "id"
                        ),
                        "score": item.get(
                            "score"
                        ),
                        "text": item.get(
                            "text"
                        ),
                        "metadata": item.get(
                            "metadata",
                            {},
                        ),
                    }
                )

            # Remove duplicate IDs.
            unique = {}

            for item in matches:

                item_id = str(
                    item.get(
                        "id",
                        "",
                    )
                )

                if item_id not in unique:
                    unique[item_id] = item

            result[
                category
            ] = list(
                unique.values()
            )[:5]

        # ------------------------------------------------------------
        # RULES
        # ------------------------------------------------------------

        result[
            "deterministic_rules"
        ] = self._compact_rules(
            rules
        )

        # ------------------------------------------------------------
        # TABLES
        # ------------------------------------------------------------

        result[
            "tables"
        ] = self._compact_tables(
            tables
        )

        return result

    def _compact_tables(
        self,
        tables: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        result = []

        for table in tables or []:

            if not isinstance(
                table,
                dict,
            ):
                continue

            result.append(
                {
                    "id": table.get(
                        "id",
                        table.get(
                            "table_id",
                            "",
                        ),
                    ),

                    "name": table.get(
                        "name",
                        table.get(
                            "title",
                            "",
                        ),
                    ),

                    "page": table.get(
                        "page"
                    ),

                    "headers": table.get(
                        "headers",
                        [],
                    ),

                    "rows": (
                        table.get(
                            "rows",
                            [],
                        )[:30]
                        if isinstance(
                            table.get(
                                "rows",
                                [],
                            ),
                            list,
                        )
                        else []
                    ),
                }
            )

        return result


    def _compact_rules(
        self,
        rules: list[Any],
    ) -> list[dict[str, Any]]:

     result = []

     for rule in rules or []:

        if isinstance(rule, dict):

            result.append(
                {
                    "id": str(
                        rule.get(
                            "rule_id",
                            rule.get(
                                "id",
                                "",
                            ),
                        )
                        or ""
                    ),

                    "name": str(
                        rule.get(
                            "name",
                            "",
                        )
                        or ""
                    ),

                    "category": str(
                        rule.get(
                            "category",
                            "",
                        )
                        or ""
                    ),

                    "description": str(
                        rule.get(
                            "description",
                            "",
                        )
                        or ""
                    ),

                    "status": str(
                        rule.get(
                            "status",
                            "",
                        )
                        or ""
                    ),

                    "condition": self._json_safe(
                        rule.get(
                            "condition",
                            {},
                        )
                    ),

                    "reason": str(
                        rule.get(
                            "reason",
                            "",
                        )
                        or ""
                    ),

                    "result": self._json_safe(
                        rule.get(
                            "result",
                            {},
                        )
                    ),
                }
            )

        else:

            result.append(
                {
                    "id": str(
                        getattr(
                            rule,
                            "rule_id",
                            getattr(
                                rule,
                                "id",
                                "",
                            ),
                        )
                        or ""
                    ),

                    "name": str(
                        getattr(
                            rule,
                            "name",
                            "",
                        )
                        or ""
                    ),

                    "category": str(
                        getattr(
                            rule,
                            "category",
                            "",
                        )
                        or ""
                    ),

                    "description": str(
                        getattr(
                            rule,
                            "description",
                            "",
                        )
                        or ""
                    ),

                    "status": str(
                        getattr(
                            rule,
                            "status",
                            "",
                        )
                        or ""
                    ),

                    "condition": self._json_safe(
                        getattr(
                            rule,
                            "condition",
                            {},
                        )
                    ),

                    "reason": str(
                        getattr(
                            rule,
                            "reason",
                            "",
                        )
                        or ""
                    ),

                    "result": self._json_safe(
                        getattr(
                            rule,
                            "result",
                            {},
                        )
                    ),
                }
            )

     return result



                
   

# ============================================================================
# BACKWARD COMPA  TIBILITY
# ============================================================================

ConstraintDiscoveryService = (
    ConstraintDiscovery
)