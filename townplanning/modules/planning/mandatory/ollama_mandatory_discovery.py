from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import requests

from townplanning.core.settings import get_settings


# ======================================================================
# DISCOVERED CONSTRAINT
# ======================================================================


@dataclass
class DiscoveredConstraint:
    field: str
    value: Any
    unit: str | None = None
    source_text: str = ""
    source_reference: str | None = None


# ======================================================================
# DISCOVERED RULE
# ======================================================================


@dataclass
class DiscoveredRule:
    candidate: bool
    title: str

    regulation_number: str | None = None
    clause: str | None = None

    required_facts: list[str] = field(
        default_factory=list
    )

    conditions: list[dict[str, Any]] = field(
        default_factory=list
    )

    constraints: list[DiscoveredConstraint] = field(
        default_factory=list
    )

    source_text: str = ""
    source_reference: str | None = None

    reason: str = ""


# ======================================================================
# OLLAMA MANDATORY DISCOVERY
# ======================================================================


class OllamaMandatoryDiscovery:
    """
    Ollama-based discovery of mandatory building-design provisions.

    IMPORTANT ARCHITECTURE:

        PlanningFacts
             |
             v
        Ollama discovery
             |
             +---- candidate?
             |
             +---- applicability conditions
             |
             +---- missing facts
             |
             +---- deterministic constraints
             |
             v
        source-grounded validation

    This class DOES NOT:

        - filter PostgreSQL rules
        - invent regulations
        - calculate unsupported values
        - modify PlanningFacts
        - decide building design
        - use general regulatory knowledge

    Ollama is used as a discovery/extraction layer.

    Regulatory values must be explicitly present in the supplied
    regulation text.

    Every deterministic constraint must contain source_text that
    can be located in the authoritative supplied source.
    """

    # ==================================================================
    # SYSTEM PROMPT
    # ==================================================================

    SYSTEM_PROMPT = r"""
You are a regulatory extraction engine for UDCPR building regulations.

Your task is NOT to design a building.

Your task is NOT to provide general planning knowledge.

Your task is NOT to use regulations that are not contained in the
supplied authoritative regulation text.

Your task is:

1. determine whether the supplied regulation provision is relevant
   to the supplied PlanningFacts

2. determine the applicability conditions

3. determine whether any required facts are genuinely missing

4. extract EVERY deterministic mandatory building-design constraint
   explicitly supported by the supplied regulation text

5. preserve the exact regulatory source wording

6. never invent a regulatory value

============================================================
PLANNING FACT MAPPING
============================================================

The regulation may use terminology that differs from PlanningFacts.

Before declaring a fact missing, inspect ALL supplied PlanningFacts.

Equivalent terminology should be mapped where the meaning is clearly
the same.

Examples:

"applicable authority"
"planning authority"
"municipal authority"
"local authority"

may correspond to:

planning_authority
municipality
development_authority

Do NOT request a fact that already exists under an equivalent field.

For example:

planning_authority = Municipal Corporation
municipality = Pune

means that "applicable authority" is NOT automatically missing.

Likewise:

"residential zone"
"R-1"
"Residential Zone - R-1"

may correspond to:

zone_type
land_use_zone
land_use_classification

when determining applicability.

Do NOT invent equivalence when the meaning is genuinely different.

============================================================
STRICT SOURCE RULES
============================================================

1. Use ONLY the supplied regulation text for regulatory values.

2. Never invent a regulatory value.

3. Never use your own UDCPR knowledge to fill a missing value.

4. Never infer a missing site fact.

5. Never infer that a special condition exists merely because it is
   common in a particular city.

6. city=Pune does NOT automatically mean every Pune-specific rule applies.

7. building_use=residential does NOT automatically satisfy every
   special residential condition.

8. If a required planning fact is genuinely absent, put it in
   required_facts.

9. Do not report a fact as missing when an equivalent supplied
   PlanningFacts field already provides it.

10. Distinguish mandatory requirements from:

    - incentives
    - premium options
    - TDR entitlement
    - optional benefits
    - recommendations
    - examples
    - explanatory notes

11. Do not treat premium FSI as mandatory merely because it appears
    in a table.

12. Do not treat TDR loading as mandatory merely because it appears
    in a table.

13. Extract those values only when the source explicitly establishes
    that they are applicable/required for the requested calculation.

============================================================
DETERMINISTIC CONSTRAINT EXTRACTION
============================================================

EXTRACTION IS REQUIRED whenever an applicable regulatory provision
contains an explicit deterministic value.

If the applicable source explicitly states a value, extract it.

Examples:

    Basic FSI: 1.00

must produce a constraint such as:

    field = basic_fsi
    value = 1.00
    source_text = "Basic FSI: 1.00"

If the applicable source explicitly states:

    Maximum building potential: 2.50

extract:

    field = maximum_fsi
    value = 2.50
    source_text = "Maximum building potential: 2.50"

Do NOT return constraints=[] merely because the value is inside a
table.

Tables are authoritative regulatory source material.

============================================================
TABLE EXTRACTION
============================================================

When a table row is applicable to the supplied PlanningFacts:

1. identify the applicable row

2. identify the applicable column

3. extract explicit deterministic values from that row/column

4. create one constraint object per deterministic value

5. preserve the supporting source text

For example, if the applicable table contains:

    Road width:
    12 m and above but below 15 m

    Basic FSI:
    1.00

    FSI on payment of premium:
    0.50

    Maximum permissible TDR loading:
    1.00

    Maximum building potential:
    2.50

then the applicable deterministic values must be considered for
extraction.

However:

- basic FSI is a deterministic value
- maximum building potential is a deterministic upper limit
- premium FSI must not automatically be classified as mandatory
- TDR must not automatically be classified as mandatory

The source wording and context determine whether optional values
are mandatory.

============================================================
NO UNSUPPORTED CALCULATION
============================================================

Do not calculate a value unless:

1. the regulation explicitly provides a formula, AND
2. all formula inputs are present in PlanningFacts.

If the regulation directly provides the value, use the provided value.

Do not recalculate it.

============================================================
SOURCE TEXT REQUIREMENT
============================================================

Every deterministic constraint MUST contain:

    source_text

The source_text must be copied VERBATIM from the supplied regulation
text.

Do NOT paraphrase it.

Do NOT summarize it.

Do NOT invent a citation.

The source_text must be sufficient to support the extracted value.

Whitespace differences are acceptable to the validator, but the
actual words and value must come from the supplied source.

============================================================
CONDITION EXTRACTION
============================================================

Conditions should describe facts that make the provision applicable.

For example:

    {
      "field": "road_width",
      "operator": ">=",
      "value": 12.0
    }

and:

    {
      "field": "road_width",
      "operator": "<",
      "value": 15.0
    }

Use canonical PlanningFacts field names where possible.

============================================================
REQUIRED FACTS
============================================================

Only put a field into required_facts if it is genuinely needed to
resolve applicability or select the applicable regulatory value AND
that fact is not present in PlanningFacts.

Do not put a regulatory result into required_facts.

For example:

"applicable authority"

must NOT be returned as a required fact when:

    planning_authority = Municipal Corporation

is already supplied.

============================================================
MANDATORY VS OPTIONAL
============================================================

A regulatory table can contain both mandatory and optional values.

Do not automatically classify every table number as mandatory.

For example:

    Basic FSI
    Premium FSI
    TDR loading
    Maximum building potential

must be interpreted according to the wording and context supplied
by the authoritative source.

Never convert an optional entitlement into a mandatory requirement.

============================================================
OUTPUT
============================================================

Return JSON ONLY.

The JSON must have this structure:

{
  "candidate": true,
  "title": "...",
  "regulation_number": "...",
  "clause": "...",

  "required_facts": [],

  "conditions": [
    {
      "field": "...",
      "operator": "...",
      "value": "..."
    }
  ],

  "constraints": [
    {
      "field": "...",
      "value": "...",
      "unit": "...",
      "source_text": "...",
      "source_reference": "..."
    }
  ],

  "source_text": "...",
  "source_reference": "...",

  "reason": "..."
}

============================================================
IMPORTANT FINAL CHECK
============================================================

Before returning JSON, verify:

- Is candidate correct?
- Are all applicable conditions included?
- Are genuinely missing facts listed?
- Did I inspect applicable tables?
- Did I extract every applicable explicit deterministic value?
- Does every constraint have source_text?
- Is every source_text actually present in the supplied regulation?
- Did I avoid inventing values?
- Did I avoid using outside regulatory knowledge?
- Did I avoid turning optional benefits into mandatory constraints?

Return JSON only.
"""

    # ==================================================================
    # INITIALIZATION
    # ==================================================================

    def __init__(self) -> None:

        settings = get_settings()

        self.host = (
            settings.OLLAMA_HOST.rstrip("/")
        )

        self.model = settings.OLLAMA_MODEL

        self.timeout = settings.OLLAMA_TIMEOUT

    # ==================================================================
    # PUBLIC API
    # ==================================================================

    def discover(
        self,
        facts: Any,
        regulation_text: str,
        source_reference: str | None = None,
    ) -> DiscoveredRule:

        if facts is None:
            raise ValueError(
                "PlanningFacts are required."
            )

        if not isinstance(
            regulation_text,
            str,
        ):
            raise TypeError(
                "regulation_text must be a string."
            )

        if not regulation_text.strip():
            raise ValueError(
                "regulation_text cannot be empty."
            )

        planning_facts = self._serialize_facts(
            facts
        )

        prompt = self._build_prompt(
            planning_facts=planning_facts,
            regulation_text=regulation_text,
            source_reference=source_reference,
        )

        # ==============================================================
        # OLLAMA
        # ==============================================================

        response = requests.post(
            f"{self.host}/api/chat",

            json={
                "model": self.model,

                "messages": [
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],

                "stream": False,

                "options": {
                    "temperature": 0,
                },

                "format": "json",
            },

            timeout=self.timeout,
        )

        response.raise_for_status()

        payload = response.json()

        content = (
            payload
            .get("message", {})
            .get("content", "")
        )

        if not content:
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        # ==============================================================
        # PARSE
        # ==============================================================

        data = self._parse_json(
            content
        )

        # ==============================================================
        # DEBUG
        #
        # This is intentionally printed while we are testing the
        # discovery engine.
        #
        # It lets us distinguish:
        #
        #   Ollama failed to extract
        #
        # from:
        #
        #   Python validator rejected extraction.
        # ==============================================================

        print()
        print("=" * 80)
        print("RAW OLLAMA JSON")
        print("=" * 80)

        print(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )
        )

        print("=" * 80)
        print()

        # ==============================================================
        # VALIDATE
        # ==============================================================

        return self._validate_result(
            data,
            regulation_text,
            source_reference,
        )

    # ==================================================================
    # PROMPT
    # ==================================================================

    def _build_prompt(
        self,
        planning_facts: dict[str, Any],
        regulation_text: str,
        source_reference: str | None,
    ) -> str:

        return f"""
PLANNING FACTS
==============

These are the complete currently detected planning facts.

Do not assume facts that are not present.

{json.dumps(
    planning_facts,
    indent=2,
    ensure_ascii=False,
)}

============================================================
SOURCE REFERENCE
============================================================

{source_reference or "Not provided"}

============================================================
AUTHORITATIVE REGULATION TEXT
============================================================

The following text is the ONLY regulatory source you may use.

Do not use outside knowledge.

---------------- BEGIN REGULATION ----------------

{regulation_text}

----------------- END REGULATION -----------------

============================================================
TASK
============================================================

Determine whether this regulation provision can impose a mandatory
building-design constraint for the supplied PlanningFacts.

If it applies:

1. identify applicability conditions

2. identify genuinely missing facts

3. inspect all applicable paragraphs and tables

4. extract EVERY applicable deterministic value explicitly stated
   in the supplied regulation

5. create one constraint object for each applicable deterministic
   value

6. copy the supporting source text VERBATIM

7. preserve the source reference

8. never invent values

9. never calculate unsupported values

10. do not classify optional premium/TDR benefits as mandatory unless
    the supplied source explicitly establishes that they are mandatory

IMPORTANT:

If the source explicitly contains:

    Basic FSI: 1.00

then constraints MUST NOT be empty merely because the value appears
inside a table.

If that value is applicable to the supplied facts, extract it.

Likewise, if the applicable source explicitly contains:

    Maximum building potential: 2.50

extract that value.

Return JSON only.
"""

    # ==================================================================
    # FACT SERIALIZATION
    # ==================================================================

    @staticmethod
    def _serialize_facts(
        facts: Any,
    ) -> dict[str, Any]:

        if hasattr(
            facts,
            "to_dict",
        ):

            values = facts.to_dict()

        elif hasattr(
            facts,
            "model_dump",
        ):

            values = facts.model_dump()

        elif isinstance(
            facts,
            dict,
        ):

            values = dict(
                facts
            )

        elif hasattr(
            facts,
            "__dict__",
        ):

            values = dict(
                vars(facts)
            )

        else:

            values = {
                "value": str(facts)
            }

        # Keep None fields.

        return values

    # ==================================================================
    # JSON PARSING
    # ==================================================================

    @staticmethod
    def _parse_json(
        content: str,
    ) -> dict[str, Any]:

        content = content.strip()

        # --------------------------------------------------------------
        # Remove fenced JSON
        # --------------------------------------------------------------

        if content.startswith(
            "```"
        ):

            content = re.sub(
                r"^```(?:json)?",
                "",
                content,
                flags=re.IGNORECASE,
            )

            content = re.sub(
                r"```$",
                "",
                content,
            ).strip()

        try:

            data = json.loads(
                content
            )

        except json.JSONDecodeError as exc:

            raise RuntimeError(
                "Ollama returned invalid JSON: "
                f"{exc}"
            ) from exc

        if not isinstance(
            data,
            dict,
        ):

            raise RuntimeError(
                "Ollama JSON response is not an object."
            )

        return data

    # ==================================================================
    # VALIDATION
    # ==================================================================

    def _validate_result(
        self,
        data: dict[str, Any],
        source_text: str,
        source_reference: str | None,
    ) -> DiscoveredRule:

        candidate = bool(
            data.get(
                "candidate",
                False,
            )
        )

        title = str(
            data.get(
                "title",
                "",
            )
        ).strip()

        if not title:
            title = (
                "Undescribed regulatory provision"
            )

        regulation_number = (
            self._optional_string(
                data.get(
                    "regulation_number"
                )
            )
        )

        clause = (
            self._optional_string(
                data.get(
                    "clause"
                )
            )
        )

        reason = str(
            data.get(
                "reason",
                "",
            )
        ).strip()

        required_facts = (
            self._string_list(
                data.get(
                    "required_facts",
                    [],
                )
            )
        )

        conditions = data.get(
            "conditions",
            [],
        )

        if not isinstance(
            conditions,
            list,
        ):

            conditions = []

        conditions = (
            self._validate_conditions(
                conditions
            )
        )

        constraints = (
            self._validate_constraints(
                data.get(
                    "constraints",
                    [],
                ),
                source_text,
                source_reference,
            )
        )

        returned_source_text = str(
            data.get(
                "source_text",
                "",
            )
        ).strip()

        # Never let Ollama replace our authoritative source.

        if not returned_source_text:
            returned_source_text = source_text

        returned_reference = (
            self._optional_string(
                data.get(
                    "source_reference"
                )
            )
            or source_reference
        )

        return DiscoveredRule(
            candidate=candidate,
            title=title,
            regulation_number=regulation_number,
            clause=clause,
            required_facts=required_facts,
            conditions=conditions,
            constraints=constraints,
            source_text=returned_source_text,
            source_reference=returned_reference,
            reason=reason,
        )

    # ==================================================================
    # CONDITION VALIDATION
    # ==================================================================

    @staticmethod
    def _validate_conditions(
        conditions: Any,
    ) -> list[dict[str, Any]]:

        if not isinstance(
            conditions,
            list,
        ):

            return []

        result = []

        for item in conditions:

            if not isinstance(
                item,
                dict,
            ):

                continue

            field_name = str(
                item.get(
                    "field",
                    "",
                )
            ).strip()

            if not field_name:
                continue

            operator = str(
                item.get(
                    "operator",
                    "==",
                )
            ).strip()

            if not operator:
                operator = "=="

            condition = {
                "field": field_name,
                "operator": operator,
            }

            if "value" in item:

                condition["value"] = (
                    item.get(
                        "value"
                    )
                )

            result.append(
                condition
            )

        return result

    # ==================================================================
    # CONSTRAINT VALIDATION
    # ==================================================================

    def _validate_constraints(
        self,
        constraints: Any,
        source_text: str,
        source_reference: str | None,
    ) -> list[DiscoveredConstraint]:

        if not isinstance(
            constraints,
            list,
        ):

            return []

        result = []

        normalized_source = (
            self._normalize_source(
                source_text
            )
        )

        for item in constraints:

            if not isinstance(
                item,
                dict,
            ):

                continue

            # ----------------------------------------------------------
            # FIELD
            # ----------------------------------------------------------

            field_name = str(
                item.get(
                    "field",
                    "",
                )
            ).strip()

            if not field_name:
                continue

            # ----------------------------------------------------------
            # VALUE
            # ----------------------------------------------------------

            if "value" not in item:
                continue

            value = item.get(
                "value"
            )

            if value is None:
                continue

            # ----------------------------------------------------------
            # SOURCE CLAIM
            # ----------------------------------------------------------

            source_claim = str(
                item.get(
                    "source_text",
                    "",
                )
            ).strip()

            if not source_claim:
                continue

            # ----------------------------------------------------------
            # SOURCE-GROUNDING CHECK
            #
            # IMPORTANT:
            #
            # We still require the claimed text to exist in the
            # authoritative source.
            #
            # We only normalize whitespace/case.
            # ----------------------------------------------------------

            normalized_claim = (
                self._normalize_source(
                    source_claim
                )
            )

            if (
                not normalized_claim
                or normalized_claim
                not in normalized_source
            ):

                continue

            # ----------------------------------------------------------
            # SOURCE REFERENCE
            # ----------------------------------------------------------

            reference = (
                self._optional_string(
                    item.get(
                        "source_reference"
                    )
                )
                or source_reference
            )

            # ----------------------------------------------------------
            # UNIT
            # ----------------------------------------------------------

            unit = (
                self._optional_string(
                    item.get(
                        "unit"
                    )
                )
            )

            result.append(
                DiscoveredConstraint(
                    field=field_name,
                    value=value,
                    unit=unit,
                    source_text=source_claim,
                    source_reference=reference,
                )
            )

        return result

    # ==================================================================
    # SOURCE NORMALIZATION
    # ==================================================================

    @staticmethod
    def _normalize_source(
        value: str,
    ) -> str:

        if not value:
            return ""

        # Normalize whitespace while preserving actual words/numbers.

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip().lower()

    # ==================================================================
    # STRING HELPERS
    # ==================================================================

    @staticmethod
    def _optional_string(
        value: Any,
    ) -> str | None:

        if value is None:
            return None

        value = str(
            value
        ).strip()

        return value or None

    @staticmethod
    def _string_list(
        value: Any,
    ) -> list[str]:

        if not isinstance(
            value,
            list,
        ):

            return []

        result = []

        for item in value:

            if item is None:
                continue

            text = str(
                item
            ).strip()

            if text:
                result.append(
                    text
                )

        return result