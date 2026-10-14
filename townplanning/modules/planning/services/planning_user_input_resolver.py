from __future__ import annotations

import json
import re
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

from townplanning.modules.planning.llm.ollama_client import OllamaClient


class PlanningUserInputResolver:
    """
    Converts explicit user answers into PlanningFacts.

    Rules:

    1. Only fields identified as missing by PlanningInputGate
       may be modified.

    2. Existing Vision-derived facts are never overwritten
       unless that field was explicitly identified as missing.

    3. No regulatory value is inferred.

    4. No LLM is called.

    5. Unrecognized user input is ignored.

    6. Derived fields such as road_widths,
       road_frontage_count and road_locations are updated
       from the canonical user input.
    """

    FIELD_ALIASES = {
        # ----------------------------------------------------------
        # Plot / site
        # ----------------------------------------------------------
        "plotArea": "plot_area",
        "plotWidth": "plot_width",
        "plotDepth": "plot_depth",
        "plotShape": "plot_shape",

        # ----------------------------------------------------------
        # Roads / access
        # ----------------------------------------------------------
        "roadWidth": "road_width",
        "road_width_m": "road_width",
        "roadFrontage": "road_frontage",
        "roadFrontages": "road_frontages",
        "roadLocations": "road_locations",
        "roadType": "road_type",
        "roadTypes": "road_types",
        "roadName": "road_name",
        "roadNames": "road_names",

        # ----------------------------------------------------------
        # Building
        # ----------------------------------------------------------
        "buildingType": "building_type",
        "buildingUse": "building_use",
        "occupancyType": "occupancy_type",
        "buildingHeight": "building_height",
        "requestedHeight": "requested_height",
        "numberOfFloors": "number_of_floors",
        "requestedFloors": "requested_floors",

        # ----------------------------------------------------------
        # Residential program
        # ----------------------------------------------------------
        "requestedUnits": "requested_units",
        "requested1bhkUnits": "requested_1bhk_units",
        "requested2bhkUnits": "requested_2bhk_units",
        "requested3bhkUnits": "requested_3bhk_units",
        "requested4bhkUnits": "requested_4bhk_units",
        "requestedOtherUnits": "requested_other_units",
        "requestedUnitMix": "requested_unit_mix",

        # ----------------------------------------------------------
        # Planning / zoning
        # ----------------------------------------------------------
        "landUseZone": "land_use_zone",
        "land_use": "land_use_zone",
        "zoning": "zone",

        # ----------------------------------------------------------
        # Access / restrictions
        # ----------------------------------------------------------
        "accessAvailable": "access_available",
        "reservationPresent": "reservation_present",
        "airportRestriction": "airport_restriction",
        "heritageZone": "heritage_zone",
        "crzZone": "crz_zone",
        "ecoSensitiveZone": "eco_sensitive_zone",
    }

    def __init__(
        self,
        ollama_client: OllamaClient | None = None,
    ):
        self.ollama_client = (
            ollama_client
            or OllamaClient()
        )

    # ==========================================================
    # OLLAMA PLANNING-FACT EXTRACTION
    # ==========================================================

    def extract_and_apply(
        self,
        facts: Any,
        user_input: str | None = None,
        images: list[str] | None = None,
        missing_information: list[Any] | None = None,
        client: Any | None = None,
    ) -> Any:
        """
        Extract planning facts from user text and optional images.

        Ollama is used only for fact extraction.

        Regulatory calculations remain outside this method.
        """

        if facts is None:
            raise ValueError(
                "facts must not be None"
            )

        user_text = str(
            user_input or ""
        ).strip()

        image_paths = [
            str(Path(item))
            for item in (images or [])
        ]

        if not user_text and not image_paths:
            return facts

        # ------------------------------------------------------
        # Determine fields supported by the existing PlanningFacts
        # object.
        # ------------------------------------------------------

        allowed_fields = self._planning_fact_fields(
            facts
        )

        # If this call comes from the existing gate flow,
        # restrict changes to fields currently identified as
        # missing.
        if missing_information is not None:

            gate_fields = self._missing_fields(
                missing_information
            )

            if gate_fields:
                allowed_fields &= gate_fields

        if not allowed_fields:
            return facts

        # ------------------------------------------------------
        # Build extraction prompt.
        # ------------------------------------------------------

        prompt = self._build_fact_extraction_prompt(
            facts=facts,
            user_input=user_text,
            allowed_fields=allowed_fields,
            images=image_paths,
        )

        # ------------------------------------------------------
        # Existing Ollama client.
        # ------------------------------------------------------

        ollama = client or self.ollama_client

        if hasattr(ollama, "generate_with_images"):
            raw_response = (
                ollama.generate_with_images(
                    prompt,
                    image_paths,
                    temperature=0.0,
                )
            )
        elif hasattr(ollama, "generate"):
            raw_response = (
                ollama.generate(
                    prompt,
                    temperature=0.0,
                    images=image_paths or None,
                )
            )
        else:
            raise TypeError(
                "Ollama client must provide "
                "generate_with_images() or generate()."
            )

        extracted = self._parse_ollama_json(
            raw_response
        )

        # ------------------------------------------------------
        # Apply only fields allowed by PlanningFacts/gate.
        # ------------------------------------------------------

        ignored_metadata_fields = {
            "missing_fields",
            "questions",
            "conflicts",
            "observations",
            "image_observations",
            "confidence",
            "sources",
        }

        for field_name, value in extracted.items():

            if field_name in ignored_metadata_fields:
                continue

            canonical_name = self.FIELD_ALIASES.get(
                field_name,
                field_name,
            )

            if canonical_name not in allowed_fields:
                continue

            if value is None:
                continue

            self._set_fact(
                facts,
                canonical_name,
                value,
            )

        # ------------------------------------------------------
        # Existing PlanningFacts normalization.
        # ------------------------------------------------------

        normalize = getattr(
            facts,
            "normalize",
            None,
        )

        if callable(normalize):
            normalize()

        return facts

    # ==========================================================
    # PLANNING FACT FIELDS
    # ==========================================================

    @staticmethod
    def _planning_fact_fields(
        facts: Any,
    ) -> set[str]:

        if is_dataclass(facts):

            return {
                item.name
                for item in fields(facts)
                if not item.name.startswith("_")
                and item.name not in {
                    "values",
                    "fact_sources",
                    "fact_confidence",
                    "fact_evidence",
                }
            }

        if isinstance(facts, dict):

            return {
                str(key)
                for key in facts
                if str(key) not in {
                    "values",
                    "fact_sources",
                    "fact_confidence",
                    "fact_evidence",
                }
            }

        return {
            name
            for name in dir(facts)
            if not name.startswith("_")
        }

    # ==========================================================
    # OLLAMA PROMPT
    # ==========================================================

    @classmethod
    def _build_fact_extraction_prompt(
        cls,
        facts: Any,
        user_input: str,
        allowed_fields: set[str],
        images: list[str],
    ) -> str:

        allowed_json = json.dumps(
            sorted(allowed_fields),
            ensure_ascii=False,
            indent=2,
        )

        existing = {}

        to_dict = getattr(
            facts,
            "to_dict",
            None,
        )

        if callable(to_dict):

            try:
                existing = dict(
                    to_dict()
                )
            except Exception:
                existing = {}

        existing_json = json.dumps(
            existing,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        return f"""
You are the planning input fact extraction component of an
AI town-planning system.

Extract ONLY explicit planning facts from the user's text
and supplied site/building images.

You are NOT the regulatory engine.

DO NOT calculate or invent:

FSI
permissible FSI
basic FSI
premium FSI
TDR
setbacks
margins
parking requirements
fire requirements
permissible building height
permissible floor count
lift requirements
staircase requirements
amenity requirements
recreational open-space requirements

Those values are determined later by the deterministic
UDCPR planning engine.

============================================================
ALLOWED FIELDS
============================================================

{allowed_json}

============================================================
CURRENT FACTS
============================================================

{existing_json}

============================================================
USER INPUT
============================================================

{user_input}

============================================================
IMAGE OBSERVATION
============================================================

Read explicit information visible in the images, including:

- written plot dimensions
- written road dimensions
- road position
- north arrow
- plot boundary
- existing building footprint
- existing building dimensions
- visible entrances/access
- surrounding roads
- annotations
- parking areas
- orientation

Do not invent measurements.

Do not estimate exact dimensions from image scale.

If information is unclear, omit it.

============================================================
OUTPUT
============================================================

Return ONLY a JSON object.

Example:

{{
  "plot_width": 40,
  "plot_depth": 50,
  "road_width": 12,
  "road_frontage": ["south"],
  "building_use": "residential"
}}

Rules:

1. Use only fields from ALLOWED FIELDS.
2. Do not invent values.
3. Do not calculate regulatory values.
4. Do not explain the response.
5. Return valid JSON only.
6. Numeric values must be numeric.
7. Boolean values must be true or false.
8. Omit unknown values.
"""

    # ==========================================================
    # OLLAMA JSON PARSER
    # ==========================================================

    @staticmethod
    def _parse_ollama_json(
        raw_response: str,
    ) -> dict[str, Any]:
        """
        Parse the structured Ollama fact-extraction response.

        Supported response forms:

            {
                "facts": {
                    "plot_area": 2000
                },
                "conflicts": [],
                "unreadable_or_uncertain": []
            }

        or:

            {
                "plot_area": 2000
            }

        Only the actual fact dictionary is returned.
        """

        if not raw_response:
            return {}

        try:
            data = json.loads(raw_response)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}

        if not isinstance(data, dict):
            return {}

        # Preferred structured response.
        facts = data.get("facts")

        if isinstance(facts, dict):
            return facts

        # Also accept a direct fact object.
        return data

    def apply(
        self,
        facts: Any,
        missing_information: list[Any],
        user_input: str | dict[str, Any],
    ) -> Any:
        """
        Apply user answers only to fields currently marked
        as missing.

        Examples:

            {
                "road_width": 18,
                "road_frontage": "south",
                "access_available": True,
                "zone": "Residential",
                "reservation_present": False,
            }

        Or:

            "18 m road, south side, access available,
             residential zone, no reservation"

        Existing facts are preserved unless the corresponding
        field was explicitly identified as missing.
        """

        allowed_fields = self._missing_fields(
            missing_information
        )

        if not allowed_fields:
            return facts

        # ------------------------------------------------------
        # Structured user input
        # ------------------------------------------------------

        if isinstance(
            user_input,
            dict,
        ):

            values = dict(
                user_input
            )

        # ------------------------------------------------------
        # Natural-language user input
        # ------------------------------------------------------

        else:

            values = self._parse_text(
                user_input,
                allowed_fields,
            )

        # ------------------------------------------------------
        # Apply only fields allowed by the gate
        # ------------------------------------------------------

        for field_name, value in values.items():

            field_name = self.FIELD_ALIASES.get(
                field_name,
                field_name,
            )

            if field_name not in allowed_fields:
                continue

            if value is None:
                continue

            self._set_fact(
                facts,
                field_name,
                value,
            )

        return facts

    # ==========================================================
    # MISSING FIELDS
    # ==========================================================

    @classmethod
    def _missing_fields(
        cls,
        missing_information: list[Any],
    ) -> set[str]:

        result: set[str] = set()

        for item in missing_information:

            if isinstance(
                item,
                dict,
            ):

                field = item.get(
                    "field"
                )

            else:

                field = getattr(
                    item,
                    "field",
                    None,
                )

            if not field:
                continue

            field = cls.FIELD_ALIASES.get(
                field,
                field,
            )

            result.add(
                field
            )

        return result

    # ==========================================================
    # TEXT PARSER
    # ==========================================================

    @classmethod
    def _parse_text(
        cls,
        text: str,
        allowed_fields: set[str],
    ) -> dict[str, Any]:
        """
        Parse explicit user answers.

        This parser does NOT infer planning or regulatory
        information. It only recognizes explicit statements.
        """

        text = str(
            text
        ).strip()

        result: dict[str, Any] = {}

        # ======================================================
        # ROAD WIDTH
        # ======================================================

        if "road_width" in allowed_fields:

            patterns = (
                # road width is 18 m
                r"\broad\s*(?:width)?\s*"
                r"(?:is|:|=)?\s*"
                r"(\d+(?:\.\d+)?)\s*"
                r"(?:m|meter|meters|metre|metres)\b",

                # 18 m wide road
                r"\b(\d+(?:\.\d+)?)\s*"
                r"(?:m|meter|meters|metre|metres)"
                r"\s*(?:wide\s*)?road\b",

                # 18m road
                r"\b(\d+(?:\.\d+)?)\s*"
                r"(?:m|meter|meters|metre|metres)"
                r"\s+road\b",

                # road is 18
                r"\broad\s+is\s+"
                r"(\d+(?:\.\d+)?)\b",
            )

            for pattern in patterns:

                match = re.search(
                    pattern,
                    text,
                    re.IGNORECASE,
                )

                if not match:
                    continue

                try:

                    result["road_width"] = float(
                        match.group(1)
                    )

                    break

                except (
                    TypeError,
                    ValueError,
                ):

                    pass

        # ======================================================
        # ROAD FRONTAGE
        # ======================================================

        if "road_frontage" in allowed_fields:

            sides = (
                "north-east",
                "north-west",
                "south-east",
                "south-west",
                "north",
                "south",
                "east",
                "west",
            )

            found_sides: list[str] = []

            for side in sides:

                if re.search(
                    rf"\b{re.escape(side)}\b",
                    text,
                    re.IGNORECASE,
                ):

                    found_sides.append(
                        side
                    )

            if found_sides:

                result["road_frontage"] = (
                    found_sides
                )

        # ======================================================
        # ACCESS
        # ======================================================

        if "access_available" in allowed_fields:

            negative_patterns = (
                r"\bno\s+(?:vehicular\s+)?access\b",
                r"\bno\s+vehicle\s+access\b",
                r"\bwithout\s+(?:vehicular\s+)?access\b",
                r"\bnot\s+accessible\b",
                r"\baccess\s+(?:is\s+)?not\s+available\b",
                r"\bno\s+access\b",
                r"\baccess\s+unavailable\b",
            )

            positive_patterns = (
                r"\byes\b",
                r"\bavailable\b",
                r"\bhas\s+(?:vehicular\s+)?access\b",
                r"\bvehicle\s+access\b",
                r"\bvehicular\s+access\b",
                r"\baccessible\b",
                r"\baccess\s+(?:is\s+)?available\b",
                r"\baccess\s+exists\b",
            )

            if any(
                re.search(
                    pattern,
                    text,
                    re.IGNORECASE,
                )
                for pattern in negative_patterns
            ):

                result[
                    "access_available"
                ] = False

            elif any(
                re.search(
                    pattern,
                    text,
                    re.IGNORECASE,
                )
                for pattern in positive_patterns
            ):

                result[
                    "access_available"
                ] = True

        # ======================================================
        # ZONE / ZONING
        # ======================================================

        if "zone" in allowed_fields:

            zone_patterns = (
                r"(?:zone|zoning|land[- ]use)"
                r"\s*(?:is|:|=)?\s*"
                r"([A-Za-z][A-Za-z0-9 /_-]*)"
            )

            match = re.search(
                zone_patterns,
                text,
                re.IGNORECASE,
            )

            if match:

                zone = match.group(
                    1
                ).strip(
                    " .,;"
                )

                if zone:

                    result["zone"] = zone

            # --------------------------------------------------
            # Common explicit form:
            #
            # Residential zone
            # Commercial zone
            # Industrial zone
            # --------------------------------------------------

            if "zone" not in result:

                common_zones = (
                    "residential",
                    "commercial",
                    "industrial",
                    "mixed-use",
                    "mixed use",
                    "agricultural",
                    "institutional",
                )

                for zone in common_zones:

                    if re.search(
                        rf"\b{re.escape(zone)}\s+zone\b",
                        text,
                        re.IGNORECASE,
                    ):

                        result["zone"] = zone

                        break

        # ======================================================
        # RESERVATION
        # ======================================================

        if "reservation_present" in allowed_fields:

            negative_patterns = (
                r"\bno\s+reservation\b",
                r"\bno\s+reservations\b",
                r"\bwithout\s+reservation\b",
                r"\bnot\s+reserved\b",
                r"\bno\s+public\s+reservation\b",
                r"\bno\s+reservation\s+on\s+the\s+plot\b",
            )

            positive_patterns = (
                r"\breservation\b",
                r"\breserved\b",
                r"\bpublic\s+purpose\b",
                r"\bpublic\s+reservation\b",
                r"\bplot\s+is\s+reserved\b",
            )

            if any(
                re.search(
                    pattern,
                    text,
                    re.IGNORECASE,
                )
                for pattern in negative_patterns
            ):

                result[
                    "reservation_present"
                ] = False

            elif any(
                re.search(
                    pattern,
                    text,
                    re.IGNORECASE,
                )
                for pattern in positive_patterns
            ):

                result[
                    "reservation_present"
                ] = True

        # ======================================================
        # AIRPORT RESTRICTION
        # ======================================================

        if "airport_restriction" in allowed_fields:

            if re.search(
                r"\bno\s+airport\s+restriction\b",
                text,
                re.IGNORECASE,
            ):

                result[
                    "airport_restriction"
                ] = False

            elif re.search(
                r"\bairport\s+restriction\b"
                r"|\bairport\s+restricted\b",
                text,
                re.IGNORECASE,
            ):

                result[
                    "airport_restriction"
                ] = True

        # ======================================================
        # HERITAGE ZONE
        # ======================================================

        if "heritage_zone" in allowed_fields:

            if re.search(
                r"\bno\s+heritage\b"
                r"|\bnot\s+heritage\b"
                r"|\bno\s+heritage\s+zone\b",
                text,
                re.IGNORECASE,
            ):

                result[
                    "heritage_zone"
                ] = False

            elif re.search(
                r"\bheritage\s+(?:zone|area)\b"
                r"|\bheritage\b",
                text,
                re.IGNORECASE,
            ):

                result[
                    "heritage_zone"
                ] = True

        # ======================================================
        # CRZ ZONE
        # ======================================================

        if "crz_zone" in allowed_fields:

            if re.search(
                r"\bno\s+crz\b"
                r"|\bnot\s+crz\b",
                text,
                re.IGNORECASE,
            ):

                result[
                    "crz_zone"
                ] = False

            elif re.search(
                r"\bcrz\b"
                r"|\bcoastal\s+regulation\s+zone\b",
                text,
                re.IGNORECASE,
            ):

                result[
                    "crz_zone"
                ] = True

        # ======================================================
        # ECO-SENSITIVE ZONE
        # ======================================================

        if "eco_sensitive_zone" in allowed_fields:

            if re.search(
                r"\bno\s+eco[- ]sensitive\b"
                r"|\bnot\s+eco[- ]sensitive\b",
                text,
                re.IGNORECASE,
            ):

                result[
                    "eco_sensitive_zone"
                ] = False

            elif re.search(
                r"\beco[- ]sensitive\s+zone\b"
                r"|\beco[- ]sensitive\b",
                text,
                re.IGNORECASE,
            ):

                result[
                    "eco_sensitive_zone"
                ] = True

        return result

    # ==========================================================
    # FACT UPDATE
    # ==========================================================

    @classmethod
    def _set_fact(
        cls,
        facts: Any,
        field_name: str,
        value: Any,
    ) -> None:

        field_name = cls.FIELD_ALIASES.get(
            field_name,
            field_name,
        )

        # ======================================================
        # ROAD WIDTH
        # ======================================================

        if field_name == "road_width":

            try:

                width = float(
                    value
                )

            except (
                TypeError,
                ValueError,
            ):

                return

            if isinstance(
                facts,
                dict,
            ):

                facts[
                    "road_width"
                ] = width

                widths = facts.get(
                    "road_widths",
                    [],
                )

                if not isinstance(
                    widths,
                    list,
                ):

                    widths = []

                if width not in widths:

                    widths.append(
                        width
                    )

                facts[
                    "road_widths"
                ] = widths

            else:

                if not hasattr(
                    facts,
                    "road_width",
                ):

                    return

                facts.road_width = width

                if not hasattr(
                    facts,
                    "road_widths",
                ):

                    return

                if not facts.road_widths:

                    facts.road_widths = [
                        width
                    ]

            return

        # ======================================================
        # ROAD FRONTAGE
        # ======================================================

        if field_name == "road_frontage":

            # --------------------------------------------------
            # Normalize input to a list of sides.
            # --------------------------------------------------

            if isinstance(
                value,
                str,
            ):

                frontage = [
                    value.strip().lower()
                ]

            elif isinstance(
                value,
                (list, tuple, set),
            ):

                frontage = [
                    str(item).strip().lower()
                    for item in value
                    if str(item).strip()
                ]

            else:

                frontage = [
                    str(value).strip().lower()
                ]

            # --------------------------------------------------
            # Remove duplicates while preserving order.
            # --------------------------------------------------

            frontage = list(
                dict.fromkeys(
                    frontage
                )
            )

            # --------------------------------------------------
            # Dictionary facts
            # --------------------------------------------------

            if isinstance(
                facts,
                dict,
            ):

                facts[
                    "road_frontage"
                ] = frontage

                facts[
                    "road_locations"
                ] = frontage

                facts[
                    "road_frontage_count"
                ] = len(
                    frontage
                )

            # --------------------------------------------------
            # PlanningFacts object
            # --------------------------------------------------

            else:

                if hasattr(
                    facts,
                    "road_locations",
                ):

                    facts.road_locations = (
                        frontage
                    )

                if hasattr(
                    facts,
                    "road_frontage_count",
                ):

                    facts.road_frontage_count = (
                        len(frontage)
                    )

            return

        # ======================================================
        # ACCESS
        # ======================================================

        if field_name == "access_available":

            if isinstance(
                value,
                str,
            ):

                normalized = (
                    value
                    .strip()
                    .lower()
                )

                if normalized in (
                    "true",
                    "yes",
                    "y",
                    "available",
                    "accessible",
                ):

                    value = True

                elif normalized in (
                    "false",
                    "no",
                    "n",
                    "not available",
                    "unavailable",
                    "not accessible",
                ):

                    value = False

                else:

                    return

            elif not isinstance(
                value,
                bool,
            ):

                return

        # ======================================================
        # BOOLEAN PLANNING FLAGS
        # ======================================================

        if field_name in (
            "reservation_present",
            "airport_restriction",
            "heritage_zone",
            "crz_zone",
            "eco_sensitive_zone",
        ):

            if isinstance(
                value,
                str,
            ):

                normalized = (
                    value
                    .strip()
                    .lower()
                )

                if normalized in (
                    "true",
                    "yes",
                    "y",
                    "present",
                    "applicable",
                    "restricted",
                    "reserved",
                ):

                    value = True

                elif normalized in (
                    "false",
                    "no",
                    "n",
                    "none",
                    "not present",
                    "not applicable",
                    "not restricted",
                    "not reserved",
                ):

                    value = False

                else:

                    return

            elif not isinstance(
                value,
                bool,
            ):

                return

        # ======================================================
        # NORMAL FIELD
        # ======================================================

        if isinstance(
            facts,
            dict,
        ):

            facts[
                field_name
            ] = value

            return

        if not hasattr(
            facts,
            field_name,
        ):

            return

        setattr(
            facts,
            field_name,
            value
        )