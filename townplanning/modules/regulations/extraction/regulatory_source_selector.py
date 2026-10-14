from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


class RegulatorySourceSelector:
    """
    Select canonical regulatory source records relevant to a query.

    This class ONLY selects supplied source IDs.

    It does not:
      - calculate regulations
      - interpret regulatory values
      - modify the database
      - invent source IDs
      - decide the final regulatory answer
    """

    #DEFAULT_MODEL = "gemma3:12b"

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
    # PUBLIC
    # ==================================================================

    def select(
        self,
        query: str,
        sources: list[Any],
        requested_fields: list[str] | None = None,
        max_sources: int = 4,
    ) -> list[str]:

        requested_fields = (
            requested_fields or []
        )

        if not sources:
            return []

        candidates = (
            self._build_candidates(
                sources
            )
        )

        if not candidates:
            return []

        prompt = self._build_prompt(
            query=query,
            candidates=candidates,
            requested_fields=requested_fields,
            max_sources=max_sources,
        )

        raw = self._call_openai(
            prompt
        )

        print()
        print("=" * 100)
        print("REGULATORY SOURCE SELECTOR")
        print("=" * 100)
        print("QUERY:", query)
        print("MODEL:", self.model)
        print()
        #print("RAW SOURCE SELECTOR RESPONSE:")
        print("RAW OPENAI SOURCE SELECTOR RESPONSE:")
        print(raw)
        print("=" * 100)
        print()

        parsed = self._parse_response(
            raw
        )

        return self._validate_selection(
            parsed=parsed,
            candidates=candidates,
            max_sources=max_sources,
        )

    # ==================================================================
    # CANDIDATES
    # ==================================================================

    @staticmethod
    def _build_candidates(
        sources: list[Any],
    ) -> list[dict[str, Any]]:

        candidates = []

        for source in sources:

            source_id = getattr(
                source,
                "source_id",
                None,
            )

            if not source_id:
                continue

            text = str(
                getattr(
                    source,
                    "text",
                    "",
                )
                or ""
            ).strip()

            if not text:
                continue

            candidates.append(
                {
                    "source_id": str(
                        source_id
                    ),
                    "regulation_number": (
                        getattr(
                            source,
                            "regulation_number",
                            None,
                        )
                    ),
                    "page": getattr(
                        source,
                        "page",
                        None,
                    ),
                    "source_type": getattr(
                        source,
                        "source_type",
                        None,
                    ),
                    "table_number": getattr(
                        source,
                        "table_number",
                        None,
                    ),
                    "table_title": getattr(
                        source,
                        "table_title",
                        None,
                    ),
                    "text": text,
                }
            )

        return candidates

    # ==================================================================
    # OPENAI
    # ==================================================================

    def _call_openai(
        self,
        prompt: str,
    ) -> str:

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "regulatory_source_selection",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "selected_source_ids": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": [
                            "selected_source_ids"
                        ],
                        "additionalProperties": False,
                    },
                },
                "verbosity": "low",
            },
            max_output_tokens=1000,
        )

        raw = response.output_text

        if not raw:
            raise RuntimeError(
                "OpenAI returned an empty "
                "source-selector response."
            )

        return raw.strip()
    # ==================================================================
    # PROMPT
    # ==================================================================

    @staticmethod
    def _build_prompt(
        query: str,
        candidates: list[dict[str, Any]],
        requested_fields: list[str],
        max_sources: int,
    ) -> str:

        blocks = []

        for index, candidate in enumerate(
            candidates,
            start=1,
        ):

            text = candidate["text"]

            # Keep enough evidence for source identification while
            # preventing an enormous prompt.
            if len(text) > 7000:
                text = (
                    text[:7000]
                    + "\n[TRUNCATED]"
                )

            blocks.append(
                "\n".join(
                    [
                        f"===== SOURCE {index} =====",
                        (
                            "SOURCE_ID: "
                            f"{candidate['source_id']}"
                        ),
                        (
                            "REGULATION_NUMBER: "
                            f"{candidate.get('regulation_number') or ''}"
                        ),
                        (
                            "PAGE: "
                            f"{candidate.get('page') or ''}"
                        ),
                        (
                            "SOURCE_TYPE: "
                            f"{candidate.get('source_type') or ''}"
                        ),
                        (
                            "TABLE_NUMBER: "
                            f"{candidate.get('table_number') or ''}"
                        ),
                        (
                            "TABLE_TITLE: "
                            f"{candidate.get('table_title') or ''}"
                        ),
                        "SOURCE_TEXT:",
                        text,
                        f"===== END SOURCE {index} =====",
                    ]
                )
            )

        fields_json = json.dumps(
            requested_fields,
            ensure_ascii=False,
        )

        return f"""
You select relevant regulatory evidence.

USER QUERY:
{query}

REQUESTED FIELDS:
{fields_json}

You have been given numbered SOURCE records.

Your ONLY task is to select the SOURCE_ID values whose source text
is directly relevant to answering the user's query.

Do not answer the query.

Do not extract values.

Do not calculate anything.

Do not explain anything.

Do not reproduce tables.

Do not create new IDs.

A source is relevant when its actual text contains or directly defines
the regulatory concept, condition, table, exception, or supporting
provision needed for the query.

Prefer:
- the source that directly governs the requested concept
- a table when the requested answer depends on a table
- sources containing the requested conditions or dimensions

IMPORTANT QUERY-DIMENSION MATCHING:
- Identify the controlling dimension in the USER QUERY.
- If the query specifies road width, prefer a table whose rows/conditions are
  explicitly keyed by road width.
- If the query specifies plot size, prefer a table keyed by plot size.
- If the query specifies building use/type, prefer sources that explicitly
  distinguish that use/type.
- Do not select a table merely because it is in the same regulation when
  another supplied source directly matches the requested dimension.
- For FSI questions involving a road-width condition, a road-width FSI table
  is preferred over an authority/area table that lacks the requested
  road-width condition.

Do NOT select a source merely because:
- it is nearby in the document
- it mentions another regulation
- it contains the same generic word
- it belongs to the same database regulation record

Return ONLY this JSON object:

{{
  "selected_source_ids": ["SOURCE_ID"]
}}

The array may contain at most {max_sources} IDs.

Every ID MUST be copied exactly from one of the SOURCE_ID values below.

If no source is relevant, return:

{{
  "selected_source_ids": []
}}

SOURCE MATERIAL:

{chr(10).join(blocks)}

FINAL INSTRUCTION:

Return JSON DATA only.

Do not return:
- a JSON schema
- TABLE_ID
- HEADERS
- ROWS
- CELLS_VALUES
- explanations
- markdown
""".strip()

    # ==================================================================
    # PARSING
    # ==================================================================

    @staticmethod
    def _parse_response(
        raw: str,
    ) -> dict[str, Any]:

        if not raw:
            raise ValueError(
                "OpenAI returned empty source-selection JSON."
            )

        try:
            data = json.loads(raw)

        except json.JSONDecodeError as exc:

            raise ValueError(
                "OpenAI returned invalid source-selection JSON:\n"
                f"{raw}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "Source selection root must be a JSON object."
            )

        selected = data.get(
            "selected_source_ids"
        )

        if not isinstance(selected, list):
            raise ValueError(
                "'selected_source_ids' must be a list."
            )

        for source_id in selected:

            if not isinstance(
                source_id,
                str,
            ):
                raise ValueError(
                    "Every selected_source_id "
                    "must be a string."
                )

        return {
            "selected_source_ids": selected
        }
    @staticmethod
    def _validate_selection(
        parsed: dict[str, Any],
        candidates: list[dict[str, Any]],
        max_sources: int,
    ) -> list[str]:

        selected = parsed.get(
            "selected_source_ids",
            [],
        )

        if not isinstance(
            selected,
            list,
        ):

            raise ValueError(
                "'selected_source_ids' must be a list."
            )

        valid_ids = {
            candidate["source_id"]
            for candidate in candidates
        }

        result = []

        for value in selected:

            if not isinstance(
                value,
                str,
            ):
                continue

            source_id = value.strip()

            if not source_id:
                continue

            if source_id not in valid_ids:
                continue

            if source_id in result:
                continue

            result.append(
                source_id
            )

            if len(result) >= max_sources:
                break

        return result
