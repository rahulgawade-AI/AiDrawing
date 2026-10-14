from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


class RegulatoryCandidateSelector:
    """
    Select the regulation(s) that directly govern a regulatory query.

    This class intentionally does NOT:
      - calculate regulatory values
      - interpret tables
      - derive FSI/setbacks/parking/etc.
      - modify the database
      - perform Chroma retrieval

    It only selects supplied regulation candidates.

    The selector is a semantic classification/ranking stage.
    Full canonical regulatory evidence is loaded only after
    regulation selection.
    """

    DEFAULT_MODEL = "gpt-5.4-nano"

    SYSTEM_PROMPT = """
You are a regulatory candidate selector for Maharashtra UDCPR.

Your task is ONLY to select the regulation(s) from the supplied candidates
that directly govern the user's requested regulatory concept.

CRITICAL RULES:

1. Select ONLY from the supplied candidates.
2. Do NOT invent regulation numbers.
3. Prefer the regulation whose TITLE and SOURCE TEXT directly define the
   requested regulatory concept.
4. A regulation that merely REFERENCES another regulation is normally NOT
   the primary governing regulation.
5. Distinguish DIRECTLY GOVERNING regulations from CROSS-REFERENCED,
   SPECIAL-CASE, or INCIDENTAL regulations.
6. Prefer a regulation that directly defines the requested regulatory
   concept over a regulation that merely mentions that concept.
7. For a general permissible FSI question, prefer a regulation explicitly
   governing permissible FSI when it contains the governing FSI provision
   or table.
8. Do not select a special-use regulation merely because it mentions FSI.
9. Do not select a higher-FSI or incentive regulation merely because it
   references FSI when another supplied candidate directly governs the
   requested permissible FSI.
10. Return normally ONE primary regulation.
11. Return additional regulations only when they are genuinely necessary
    to answer the user's question.
12. Never calculate values.
13. Never infer missing facts.
14. Never use knowledge outside the supplied candidate text.
15. Do not confuse a regulation that REFERENCES another regulation with
    the regulation that actually defines the requested rule.
16. If a candidate contains the direct governing table or provision,
    prefer it over incidental references to that table or provision.

Example:

Question:
"What is the permissible FSI for a residential apartment building?"

If supplied candidates include:

6.3 - Permissible FSI
7.0 - General / Higher FSI
7.12 - Buildings of Smart Fin-Tech Centre

and 6.3 contains the governing permissible FSI provision/table,
select 6.3.

7.0 and 7.12 must NOT replace 6.3 merely because they mention FSI.

Return ONLY valid JSON DATA matching the supplied structured-output
contract.
""".strip()

    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "selected_regulations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "regulation_number": {
                            "type": "string",
                        },
                        "reason": {
                            "type": "string",
                        },
                        "confidence": {
                            "type": "number",
                        },
                    },
                    "required": [
                        "regulation_number",
                        "reason",
                        "confidence",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": [
            "selected_regulations"
        ],
        "additionalProperties": False,
    }

    def __init__(
        self,
        model: str | None = None,
        client: OpenAI | None = None,
    ) -> None:
        self.model = (
            model
            or os.getenv(
                "OPENAI_REGULATORY_SELECTOR_MODEL"
            )
            or self.DEFAULT_MODEL
        )

        self.client = (
            client
            or OpenAI()
        )

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        requested_fields: list[str] | None = None,
    ) -> str:

        fields = (
            requested_fields
            or []
        )

        sections: list[str] = []

        for index, candidate in enumerate(
            candidates,
            start=1,
        ):

            metadata = (
                candidate.get(
                    "metadata"
                )
                or {}
            )

            regulation_number = (
                candidate.get(
                    "regulation_number"
                )
                or metadata.get(
                    "regulation_number"
                )
                or metadata.get(
                    "regulationNumber"
                )
                or metadata.get(
                    "number"
                )
                or ""
            )

            title = (
                candidate.get(
                    "title"
                )
                or metadata.get(
                    "title"
                )
                or metadata.get(
                    "regulation_title"
                )
                or ""
            )

            source_text = (
                candidate.get(
                    "source_text"
                )
                or candidate.get(
                    "document"
                )
                or ""
            )

            distance = candidate.get(
                "distance"
            )

            source_text = str(
                source_text
            ).strip()

            # The candidate selector only needs enough source context
            # to identify the governing regulation. Full canonical
            # evidence is loaded after selection.
            max_chars = 5000

            if len(source_text) > max_chars:
                source_text = (
                    source_text[:max_chars]
                    + "\n[TRUNCATED]"
                )

            sections.append(
                f"""
--- CANDIDATE {index} ---
REGULATION_NUMBER: {regulation_number}
TITLE: {title}
RETRIEVAL_DISTANCE: {distance}

SOURCE_TEXT:
{source_text}
--- END CANDIDATE {index} ---
""".strip()
            )

        fields_text = (
            ", ".join(fields)
            if fields
            else "(not specified)"
        )

        return f"""
USER QUERY:
{query}

REQUESTED FIELDS:
{fields_text}

CANDIDATES:

{chr(10).join(sections)}

Select the regulation(s) that DIRECTLY govern the user's query.

Important:

- Return the actual regulation number, such as "6.3".
- Do NOT return "Candidate 6".
- Do NOT return the candidate index.
- Select ONLY regulation numbers present in the supplied candidates.
- Prefer the direct governing regulation over regulations that merely
  reference it.
- Prefer a candidate whose source text directly defines the requested
  regulatory concept.
- If one candidate contains the governing provision/table and another
  candidate merely references it, select the governing candidate.
- Do not select special-use provisions merely because they contain the
  same keyword as the query.
- Normally select exactly one primary regulation.
- Additional regulations should be selected only when they are genuinely
  necessary.

Return ONLY valid JSON DATA matching the structured-output contract.
""".strip()

    # ------------------------------------------------------------------
    # OpenAI call
    # ------------------------------------------------------------------

    def _call_openai(
        self,
        prompt: str,
    ) -> dict[str, Any]:

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self.SYSTEM_PROMPT,
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "regulatory_candidate_selection",
                    "description": (
                        "Select regulations that directly govern "
                        "the regulatory query."
                    ),
                    "schema": self.RESPONSE_SCHEMA,
                    "strict": True,
                }
            },
        )

        raw = response.output_text

        if not raw:
            raise RuntimeError(
                "OpenAI returned an empty regulatory "
                "selector response."
            )

        try:
            parsed = json.loads(
                raw
            )

        except json.JSONDecodeError as exc:

            raise RuntimeError(
                "OpenAI returned invalid JSON: "
                f"{raw!r}"
            ) from exc

        if not isinstance(
            parsed,
            dict,
        ):

            raise RuntimeError(
                "OpenAI selector response is not "
                "a JSON object."
            )

        return parsed

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_regulation_number(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        value = str(
            value
        ).strip()

        if value.lower().startswith(
            "candidate "
        ):
            value = value[
                10:
            ].strip()

        return value

    def _validate_selection(
        self,
        parsed: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> list[str]:

        selected = parsed.get(
            "selected_regulations"
        )

        if not isinstance(
            selected,
            list,
        ):

            raise RuntimeError(
                "OpenAI selector response does not contain "
                "'selected_regulations'."
            )

        candidate_numbers: set[str] = set()

        for candidate in candidates:

            metadata = (
                candidate.get(
                    "metadata"
                )
                or {}
            )

            number = (
                candidate.get(
                    "regulation_number"
                )
                or metadata.get(
                    "regulation_number"
                )
                or metadata.get(
                    "regulationNumber"
                )
                or metadata.get(
                    "number"
                )
            )

            if number is not None:

                candidate_numbers.add(
                    self._normalise_regulation_number(
                        number
                    )
                )

        result: list[str] = []

        for item in selected:

            if not isinstance(
                item,
                dict,
            ):
                continue

            number = (
                self._normalise_regulation_number(
                    item.get(
                        "regulation_number"
                    )
                )
            )

            if not number:
                continue

            # OpenAI is a selector, not an authority.  A model response
            # must never be allowed to introduce a regulation that Chroma
            # did not supply.  Treat such a response as an invalid selection
            # instead of crashing the complete planning-resolution pass.
            if number not in candidate_numbers:
                continue

            if number not in result:
                result.append(number)

        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        requested_fields: list[str] | None = None,
    ) -> list[str]:

        if not candidates:
            return []

        prompt = self._build_prompt(
            query=query,
            candidates=candidates,
            requested_fields=requested_fields,
        )

        parsed = self._call_openai(
            prompt
        )

        # Validation is deliberately a closed-world operation:
        # only regulation numbers present in `candidates` can leave this
        # method.  No fallback to an unselected/model-invented regulation.
        return self._validate_selection(
            parsed=parsed,
            candidates=candidates,
        )
