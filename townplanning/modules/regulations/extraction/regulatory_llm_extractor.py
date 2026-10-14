from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI


class RegulatoryLLMExtractor:
    """
    Strict source-grounded regulatory extraction engine.

    Important design rule:

    FSI values are NOT treated as one generic value when the source
    contains authority-specific alternatives.

    If the query does not specify the authority, all explicitly stated
    authority branches are preserved separately. A generic FSI value must
    not be generated when the source contains multiple authority-specific
    alternatives.

    """

    SYSTEM_PROMPT = """
You are a STRICT SOURCE-GROUNDED REGULATORY DATA EXTRACTION ENGINE.

You are given authoritative Maharashtra UDCPR regulatory source material.

Your task is to extract regulatory facts from the supplied source
material into the exact JSON schema specified by the API.

============================================================
ABSOLUTE RULES
============================================================

1. USE ONLY THE SUPPLIED SOURCE MATERIAL.

2. DO NOT USE GENERAL KNOWLEDGE.

3. DO NOT INVENT VALUES.

4. DO NOT CALCULATE VALUES.

5. DO NOT INFER VALUES.

6. DO NOT MAKE APPLICABILITY DECISIONS that are not explicitly
   supported by the source.

7. Every extracted concept MUST have:
   - field
   - value
   - unit
   - condition
   - qualifiers
   - authority
   - source_refs
   - source_text
   - confidence

8. source_refs MUST contain the exact SOURCE_ID supplied in the
   source material.

9. source_text MUST be copied exactly from the supplied source.
   Do not paraphrase source_text.

10. Preserve regulatory ranges exactly.

11. Preserve authority-specific alternatives exactly.

12. Preserve exceptions and qualifiers.

============================================================
TABLE INTERPRETATION
============================================================

Tables MUST be interpreted using their headers AND rows.

Never associate a number with a field merely because it appears
near that field.

The controlling dimension of the user's query MUST be matched
before extracting values.

Examples:

- If the query specifies ROAD WIDTH, use the row whose road-width
  range matches that road width.

- If the query specifies PLOT SIZE, use the plot-size dimension.

- If the query specifies BUILDING USE, use the building-use dimension.

- If the query specifies AUTHORITY, use the authority branch that
  explicitly matches that authority.

Do NOT substitute one table dimension for another.

============================================================
CRITICAL FSI RULES
============================================================

FSI questions require especially strict treatment.

If the query contains a road width:

1. Find the FSI table controlled by road width.

2. Find the exact row/range containing the supplied road width.

3. Extract FSI values ONLY from that row.

4. Preserve the association between:
   - Basic FSI
   - Premium FSI
   - TDR FSI
   - Maximum Building Potential / Maximum FSI

5. If the table has multiple authority/area branches, preserve
   EACH branch separately.

6. NEVER merge values from different authority branches.

7. NEVER choose one authority branch merely because it appears first.

8. NEVER create a generic "fsi" value when multiple authority
   branches exist and the user did not specify which authority applies.

9. In that situation, use explicit fields such as:
   - basic_fsi
   - premium_fsi
   - tdr_fsi
   - maximum_fsi

   and populate the authority field for EACH branch.

10. If exactly one authority branch exists, a generic "fsi" may only
    be emitted when the source explicitly defines that field/value.

11. "Maximum Building Potential" must be represented as
    "maximum_fsi" when it is the controlling maximum FSI value.

12. Do NOT calculate maximum FSI by adding Basic + Premium + TDR.
    Use only the explicitly stated maximum value.

============================================================
ROAD WIDTH MATCHING
============================================================

When a query gives a road width, the extracted condition MUST
correspond to the road-width range in the source.

For example, if the source says:

"12.0 m. and above but below 15.0 m."

then preserve that exact condition.

Do NOT replace it with:

"12 m"

Do NOT use a plot-size row simply because that row also contains
the number 12.

AUTHORITY BRANCHING
============================================================

If the supplied source contains multiple authority or area branches,
treat each explicitly stated branch as a separate regulatory branch.

They MUST remain separate.

Preserve the exact authority wording from the source on each affected
concept.

Do not merge values from different branches.

A single generic "fsi" concept is WRONG when the source contains
multiple authority-specific alternatives and the query does not identify
which branch applies.

============================================================
IRRELEVANT TABLES
============================================================

If the query asks:

"FSI for a residential apartment building with a 12 metre road"

then a table controlled primarily by plot size is NOT the controlling
table for the answer.

Ignore unrelated tables even if they have the same regulation number.

Do not extract values from:
- green belt tables
- industrial building tables
- plot-size-only tables
- unrelated building types
- unrelated regulations

merely because they are present in the supplied context.

============================================================
SOURCE PROVENANCE
============================================================

Every concept must point to the source that actually supports it.

If the source contains a table row with the exact requested condition,
use that table source.

Do not cite an unrelated regulation paragraph when the actual value
comes from a table.

============================================================
OUTPUT
============================================================

Return ONLY JSON data.

The root object MUST contain:

{
  "regulations": [...]
}

Do not return:
- markdown
- explanations
- prose
- reasoning
- table schemas
- original source objects
- headers
- rows
- cell arrays
- TABLE_ID
- arbitrary keys

If no supported facts can be extracted:

{
  "regulations": []
}
"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 180,
    ) -> None:

        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY")
        )

        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured."
            )

        self.model = (
            model
            or os.getenv(
                "OPENAI_MODEL",
                "gpt-5.6-luna",
            )
        )

        self.timeout = timeout

        self.client = OpenAI(
            api_key=self.api_key,
        )

    # ==================================================================
    # PUBLIC API
    # ==================================================================

    def extract(
        self,
        query: str,
        sources: list[Any],
        requested_fields: list[str] | None = None,
    ) -> dict[str, Any]:

        requested_fields = requested_fields or []

        prompt = self._build_prompt(
            query=query,
            sources=sources,
            requested_fields=requested_fields,
        )

        response = self.client.responses.create(
            model=self.model,
            instructions=self.SYSTEM_PROMPT,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "regulatory_extraction",
                    "strict": True,
                    "schema": self._response_schema(),
                },
                "verbosity": "low",
            },
            max_output_tokens=7000,
        )

        raw = response.output_text

        if not raw:
            raise RuntimeError(
                "OpenAI returned an empty regulatory extraction response."
            )

        raw = raw.strip()

        print()
        print("=" * 100)
        print("RAW OPENAI REGULATORY EXTRACTION RESPONSE")
        print("=" * 100)
        print(raw)
        print("=" * 100)
        print()

        result = self._parse_response(raw)
        result = self._normalize_source_refs(
            result=result,
            sources=sources,
        )

        # --------------------------------------------------------------
        # Deterministic source-safety cleanup.
        #
        # Python only removes ambiguous or clearly unrelated extracted
        # concepts. It does not calculate, derive, or invent values.
        # --------------------------------------------------------------

        result = self._post_process_result(
            result=result,
            query=query,
            requested_fields=requested_fields,
            sources=sources,
        )

        print()
        print("=" * 100)
        print("POST-PROCESSED REGULATORY EXTRACTION")
        print("=" * 100)
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )
        print("=" * 100)
        print()

        return result

    # ==================================================================
    # OPENAI SCHEMA
    # ==================================================================

    @staticmethod
    def _response_schema() -> dict[str, Any]:

        return {
            "type": "object",
            "properties": {
                "regulations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "regulation_number": {
                                "type": "string",
                            },
                            "title": {
                                "type": "string",
                            },
                            "concepts": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "field": {
                                            "type": "string",
                                        },
                                        "value": {
                                            "type": [
                                                "string",
                                                "number",
                                                "null",
                                            ],
                                        },
                                        "unit": {
                                            "type": [
                                                "string",
                                                "null",
                                            ],
                                        },
                                        "condition": {
                                            "type": "object",
                                            "properties": {
                                                "raw": {
                                                    "type": "string",
                                                },
                                                "items": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "string",
                                                    },
                                                },
                                            },
                                            "required": [
                                                "raw",
                                                "items",
                                            ],
                                            "additionalProperties": False,
                                        },
                                        "qualifiers": {
                                            "type": "array",
                                            "items": {
                                                "type": "string",
                                            },
                                        },
                                        "authority": {
                                            "type": [
                                                "string",
                                                "null",
                                            ],
                                        },
                                        "source_refs": {
                                            "type": "array",
                                            "items": {
                                                "type": "string",
                                            },
                                        },
                                        "source_text": {
                                            "type": "string",
                                        },
                                        "confidence": {
                                            "type": "number",
                                        },
                                    },
                                    "required": [
                                        "field",
                                        "value",
                                        "unit",
                                        "condition",
                                        "qualifiers",
                                        "authority",
                                        "source_refs",
                                        "source_text",
                                        "confidence",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "exceptions": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                },
                            },
                            "cross_references": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                },
                            },
                        },
                        "required": [
                            "regulation_number",
                            "title",
                            "concepts",
                            "exceptions",
                            "cross_references",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
            "required": [
                "regulations",
            ],
            "additionalProperties": False,
        }

    # ==================================================================
    # PROMPT
    # ==================================================================

    def _build_prompt(
        self,
        query: str,
        sources: list[Any],
        requested_fields: list[str],
    ) -> str:

        source_blocks: list[str] = []

        for index, source in enumerate(
            sources,
            start=1,
        ):

            source_id = self._source_value(
                source,
                "source_id",
                "",
            )

            text = self._source_value(
                source,
                "text",
                "",
            )

            regulation_number = self._source_value(
                source,
                "regulation_number",
                "",
            )

            page = self._source_value(
                source,
                "page",
                "",
            )

            source_type = self._source_value(
                source,
                "source_type",
                "",
            )

            table_number = self._source_value(
                source,
                "table_number",
                "",
            )

            table_title = self._source_value(
                source,
                "table_title",
                "",
            )

            source_blocks.append(
                "\n".join(
                    [
                        f"===== SOURCE {index} =====",
                        f"SOURCE_ID: {source_id}",
                        (
                            "REGULATION_NUMBER: "
                            f"{regulation_number or ''}"
                        ),
                        f"PAGE: {page or ''}",
                        f"SOURCE_TYPE: {source_type or ''}",
                        (
                            "TABLE_NUMBER: "
                            f"{table_number or ''}"
                        ),
                        (
                            "TABLE_TITLE: "
                            f"{table_title or ''}"
                        ),
                        "SOURCE_TEXT:",
                        str(text),
                        f"===== END SOURCE {index} =====",
                    ]
                )
            )

        return f"""
USER REGULATORY QUERY
=====================

{query}

REQUESTED FIELDS
================

{json.dumps(
    requested_fields,
    ensure_ascii=False,
)}

EXTRACTION INSTRUCTIONS
=======================

Extract ONLY regulatory facts directly supported by the supplied
source material.

The query's controlling dimension is extremely important.

If the query gives a road width:
    - identify the road-width-controlled FSI table
    - identify the exact matching road-width row
    - extract FSI values from that row
    - preserve every authority branch separately

If the source has multiple authority branches:
    - do NOT merge them
    - do NOT select one arbitrarily
    - do NOT create generic "fsi"
    - preserve authority on each FSI concept

If the source contains multiple authority or area branches,
keep every branch separate.

Do not merge values across branches.

When the query does not identify the authority, do not create a generic
"fsi" concept. Use the explicit FSI fields supported by the source, such
as:
- basic_fsi
- premium_fsi
- tdr_fsi
- maximum_fsi

and preserve the exact authority branch for each extracted concept.

Do not calculate maximum FSI.

Do not add Basic + Premium + TDR.

Use the explicitly stated maximum value.

Do not use an unrelated plot-size table for a road-width FSI query.

SOURCE MATERIAL
===============

{chr(10).join(source_blocks)}

RETURN ONLY JSON DATA.
"""

    # ==================================================================
    # SOURCE HELPERS
    # ==================================================================

    @staticmethod
    def _source_value(
        source: Any,
        key: str,
        default: Any = None,
    ) -> Any:

        if hasattr(source, key):
            return getattr(
                source,
                key,
                default,
            )

        if isinstance(source, dict):
            return source.get(
                key,
                default,
            )

        return default

    # ==================================================================
    # PARSER
    # ==================================================================

    @staticmethod
    def _parse_response(
        raw: str,
    ) -> dict[str, Any]:

        if not raw:
            raise ValueError(
                "OpenAI returned empty regulatory extraction JSON."
            )

        try:
            data = json.loads(raw)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "OpenAI returned invalid regulatory extraction JSON:\n"
                f"{raw}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "Regulatory extraction root must be an object."
            )

        if "regulations" not in data:
            raise ValueError(
                "OpenAI response missing required 'regulations' key."
            )

        if not isinstance(
            data["regulations"],
            list,
        ):
            raise ValueError(
                "'regulations' must be a list."
            )

        return data

    # ==================================================================
    # POST PROCESSING
    # ==================================================================

    def _post_process_result(
        self,
        result: dict[str, Any],
        query: str,
        requested_fields: list[str],
        sources: list[Any],
    ) -> dict[str, Any]:

        regulations = result.get(
            "regulations",
            [],
        )

        if not isinstance(
            regulations,
            list,
        ):
            return result

        road_width_query = self._query_contains_road_width(
            query
        )

        for regulation in regulations:

            if not isinstance(
                regulation,
                dict,
            ):
                continue

            concepts = regulation.get(
                "concepts",
                [],
            )

            if not isinstance(
                concepts,
                list,
            ):
                continue

            # ----------------------------------------------------------
            # STEP 1
            #
            # For road-width FSI queries, remove concepts whose evidence
            # is clearly from plot-size-only tables.
            # ----------------------------------------------------------

            if road_width_query:
                concepts = self._filter_road_width_concepts(
                    concepts
                )

            # ----------------------------------------------------------
            # STEP 2
            #
            # Determine whether FSI has multiple authority branches.
            # ----------------------------------------------------------

            fsi_concepts = [
                concept
                for concept in concepts
                if isinstance(concept, dict)
                and self._is_fsi_field(
                    concept.get("field")
                )
                and concept.get("value") is not None
            ]

            authorities = {
                self._normalize_authority(
                    concept.get("authority")
                )
                for concept in fsi_concepts
                if concept.get("authority")
            }

            authorities.discard("")

            # ----------------------------------------------------------
            # STEP 3
            #
            # If multiple authority branches exist, generic "fsi"
            # concepts are ambiguous and MUST be removed.
            # ----------------------------------------------------------

            if len(authorities) >= 2:

                cleaned: list[dict[str, Any]] = []

                for concept in concepts:

                    if not isinstance(
                        concept,
                        dict,
                    ):
                        continue

                    field = str(
                        concept.get(
                            "field",
                            "",
                        )
                        or ""
                    ).strip().lower()

                    authority = self._normalize_authority(
                        concept.get("authority")
                    )

                    if (
                        field == "fsi"
                        and not authority
                    ):
                        continue

                    cleaned.append(concept)

                concepts = cleaned

            # ----------------------------------------------------------
            # STEP 4
            #
            # If generic FSI concepts still exist with multiple values,
            # remove them. A generic FSI must never contain conflicting
            # values.
            # ----------------------------------------------------------

            generic_fsi = [
                concept
                for concept in concepts
                if isinstance(concept, dict)
                and str(
                    concept.get(
                        "field",
                        "",
                    )
                    or ""
                ).strip().lower() == "fsi"
            ]

            generic_values = {
                self._numeric_or_string_value(
                    concept.get("value")
                )
                for concept in generic_fsi
                if concept.get("value") is not None
            }

            if len(generic_values) > 1:

                concepts = [
                    concept
                    for concept in concepts
                    if not (
                        isinstance(
                            concept,
                            dict,
                        )
                        and str(
                            concept.get(
                                "field",
                                "",
                            )
                            or ""
                        ).strip().lower()
                        == "fsi"
                    )
                ]

            regulation["concepts"] = concepts

        return result

    # ==================================================================
    # ROAD WIDTH FILTER
    # ==================================================================

    @staticmethod
    def _query_contains_road_width(
        query: str,
    ) -> bool:

        if not query:
            return False

        normalized = query.lower()

        patterns = [
            r"\broad\s+width\b",
            r"\b\d+(?:\.\d+)?\s*metre(?:s)?\s+road\b",
            r"\b\d+(?:\.\d+)?\s*m\.?\s+road\b",
            r"\broad\s+of\s+\d+(?:\.\d+)?",
        ]

        return any(
            re.search(
                pattern,
                normalized,
            )
            for pattern in patterns
        )

    def _filter_road_width_concepts(
        self,
        concepts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        filtered: list[dict[str, Any]] = []

        for concept in concepts:

            if not isinstance(
                concept,
                dict,
            ):
                continue

            field = str(
                concept.get(
                    "field",
                    "",
                )
                or ""
            ).strip().lower()

            condition = concept.get(
                "condition",
                {},
            )

            source_text = str(
                concept.get(
                    "source_text",
                    "",
                )
                or ""
            ).lower()

            condition_raw = ""

            if isinstance(
                condition,
                dict,
            ):
                condition_raw = str(
                    condition.get(
                        "raw",
                        "",
                    )
                    or ""
                ).lower()

            combined = (
                condition_raw
                + " "
                + source_text
            )

            # ----------------------------------------------------------
            # Road-width evidence markers.
            # ----------------------------------------------------------

            has_road_width = bool(
                re.search(
                    r"\broad\b",
                    combined,
                )
                or re.search(
                    r"\b\d+(?:\.\d+)?\s*m\.?",
                    combined,
                )
            )

            # ----------------------------------------------------------
            # Plot-size table markers.
            # ----------------------------------------------------------

            is_plot_size_table = any(
                marker in combined
                for marker in (
                    "plot size",
                    "up to 300",
                    "above 300 and upto 500",
                    "above 500 and upto 1000",
                    "special building",
                )
            )

            # ----------------------------------------------------------
            # FSI fields need road-width evidence when the query is
            # specifically road-width controlled.
            # ----------------------------------------------------------

            if self._is_fsi_field(field):

                if is_plot_size_table and not has_road_width:
                    continue

            # A standalone road_width concept is always retained.
            #
            # Non-FSI concepts without road-width evidence are retained
            # because they may be supporting facts from the regulation.
            filtered.append(concept)

        return filtered

    # ==================================================================
    # FSI HELPERS
    # ==================================================================

    @staticmethod
    def _is_fsi_field(
        field: Any,
    ) -> bool:

        if field is None:
            return False

        normalized = str(
            field
        ).strip().lower()

        return normalized in {
            "fsi",
            "basic_fsi",
            "premium_fsi",
            "tdr_fsi",
            "maximum_fsi",
        }

    @staticmethod
    def _normalize_authority(
        authority: Any,
    ) -> str:

        if authority is None:
            return ""

        value = str(
            authority
        ).strip().lower()

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value

    @staticmethod
    def _numeric_or_string_value(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        if isinstance(
            value,
            float,
        ):
            return f"{value:.12g}"

        return str(
            value
        ).strip()

        # ==================================================================
    # SOURCE REFERENCE NORMALIZATION
    # ==================================================================

    @staticmethod
    def _normalize_source_refs(
        result: dict[str, Any],
        sources: list[Any],
    ) -> dict[str, Any]:

        canonical_ids = []

        for source in sources:
            source_id = (
                getattr(source, "source_id", None)
                if hasattr(source, "source_id")
                else (
                    source.get("source_id")
                    if isinstance(source, dict)
                    else None
                )
            )

            if source_id:
                canonical_ids.append(str(source_id))

        canonical_set = set(canonical_ids)

        if not canonical_set:
            return result

        for regulation in result.get(
            "regulations",
            [],
        ):

            if not isinstance(regulation, dict):
                continue

            for concept in regulation.get(
                "concepts",
                [],
            ):

                if not isinstance(concept, dict):
                    continue

                refs = concept.get(
                    "source_refs",
                    [],
                )

                if not isinstance(refs, list):
                    continue

                normalized_refs = []

                for ref in refs:

                    if not isinstance(
                        ref,
                        str,
                    ):
                        continue

                    ref = ref.strip()

                    # Exact match: nothing to do.
                    if ref in canonical_set:
                        normalized_refs.append(ref)
                        continue

                    # --------------------------------------------------
                    # LLM occasionally makes a tiny transcription error
                    # in a long source ID.
                    #
                    # Only accept a correction when:
                    #   - same source-id prefix
                    #   - very small edit distance
                    #
                    # This prevents arbitrary source substitution.
                    # --------------------------------------------------

                    best_match = None
                    best_distance = None

                    for canonical_id in canonical_ids:

                        distance = (
                            RegulatoryLLMExtractor
                            ._levenshtein_distance(
                                ref,
                                canonical_id,
                            )
                        )

                        if (
                            best_distance is None
                            or distance < best_distance
                        ):
                            best_distance = distance
                            best_match = canonical_id

                    # A source ID is a long cryptographic identifier.
                    # Accept only an extremely small typo.
                    if (
                        best_match is not None
                        and best_distance is not None
                        and best_distance <= 2
                        and len(ref) >= 40
                    ):
                        normalized_refs.append(
                            best_match
                        )

                    else:
                        # Preserve the original reference.
                        # Step 8 will correctly reject it.
                        normalized_refs.append(ref)

                concept["source_refs"] = list(
                    dict.fromkeys(
                        normalized_refs
                    )
                )

        return result

    # ==================================================================
    # LEVENSHTEIN DISTANCE
    # ==================================================================

    @staticmethod
    def _levenshtein_distance(
        a: str,
        b: str,
    ) -> int:

        if a == b:
            return 0

        if not a:
            return len(b)

        if not b:
            return len(a)

        previous = list(
            range(
                len(b) + 1
            )
        )

        for i, char_a in enumerate(
            a,
            start=1,
        ):

            current = [
                i
            ]

            for j, char_b in enumerate(
                b,
                start=1,
            ):

                insert_cost = (
                    current[j - 1] + 1
                )

                delete_cost = (
                    previous[j] + 1
                )

                replace_cost = (
                    previous[j - 1]
                    + (
                        0
                        if char_a == char_b
                        else 1
                    )
                )

                current.append(
                    min(
                        insert_cost,
                        delete_cost,
                        replace_cost,
                    )
                )

            previous = current

        return previous[-1]