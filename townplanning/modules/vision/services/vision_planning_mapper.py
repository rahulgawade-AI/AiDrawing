"""
Vision -> PlanningFacts mapper.

This module converts visual evidence into PlanningFacts while preserving
source provenance.

IMPORTANT SOURCE RULE:

    Explicit value found in image
        >
    Regulatory value derived from database

The mapper NEVER derives regulations.

It only records what is visibly present.

Examples:

    Image:
        "PLOT AREA 812.40 SQ.M."
        -> PlanningFacts.plot_area = 812.40

    Image:
        "Permissible FSI 2.0"
        -> PlanningFacts.fsi = 2.0
        -> source = "vision_image"

    Image does not contain FSI
        -> mapper does NOT create FSI
        -> downstream regulatory engine may derive FSI

User requirements such as BHK mix are handled separately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VisionPlanningMapResult:
    facts: Any

    mapped_fields: list[str] = field(default_factory=list)

    image_regulatory_fields: list[str] = field(
        default_factory=list
    )

    image_project_fields: list[str] = field(
        default_factory=list
    )

    evidence: dict[str, Any] = field(
        default_factory=dict
    )

    ignored_regulatory_text: list[str] = field(
        default_factory=list
    )


class VisionPlanningMapper:
    """
    Maps VisionEvidence into PlanningFacts.

    The mapper is deliberately conservative.

    It does not:
        - derive FSI
        - derive setbacks
        - derive margins
        - derive parking
        - derive fire requirements
        - derive permissible height
        - derive permissible floors
        - interpret UDCPR
    """

    SITE_FIELD_MAP = {
        "plot_area": "plot_area",
        "plot_number": "plot_number",
        "survey_number": "survey_number",
        "cts_number": "cts_number",
        "road_width": "road_width",
        "road_name": "road_name",
        "road_type": "road_type",
        "north": "north_direction",
        "scale": "scale",
    }

    IMAGE_REGULATORY_PATTERNS = {
        "fsi": [
            re.compile(
                r"\b(?:permissible|permitted|allowable)\s+fsi"
                r"\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bfsi\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
                re.IGNORECASE,
            ),
        ],

        "basic_fsi": [
            re.compile(
                r"\bbasic\s+fsi"
                r"\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
                re.IGNORECASE,
            ),
        ],

        "premium_fsi": [
            re.compile(
                r"\bpremium\s+fsi"
                r"\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
                re.IGNORECASE,
            ),
        ],

        "setback": [
            re.compile(
                r"\bsetback\b\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)"
                r"\s*(m|meter|meters|metre|metres)?",
                re.IGNORECASE,
            ),
        ],

        "front_setback": [
            re.compile(
                r"\bfront\s+setback\b\s*[:=]?\s*"
                r"([0-9]+(?:\.[0-9]+)?)"
                r"\s*(m|meter|meters|metre|metres)?",
                re.IGNORECASE,
            ),
        ],

        "side_setback": [
            re.compile(
                r"\bside\s+setback\b\s*[:=]?\s*"
                r"([0-9]+(?:\.[0-9]+)?)"
                r"\s*(m|meter|meters|metre|metres)?",
                re.IGNORECASE,
            ),
        ],

        "rear_setback": [
            re.compile(
                r"\brear\s+setback\b\s*[:=]?\s*"
                r"([0-9]+(?:\.[0-9]+)?)"
                r"\s*(m|meter|meters|metre|metres)?",
                re.IGNORECASE,
            ),
        ],

        "margin": [
            re.compile(
                r"\bmargin\b\s*[:=]?\s*"
                r"([0-9]+(?:\.[0-9]+)?)"
                r"\s*(m|meter|meters|metre|metres)?",
                re.IGNORECASE,
            ),
        ],
    }

    PROJECT_PATTERNS = {
        "building_use": re.compile(
            r"\bbuilding\s+use\b\s*[:=]\s*([^\n;]+)",
            re.IGNORECASE,
        ),

        "building_type": re.compile(
            r"\bbuilding\s+type\b\s*[:=]\s*([^\n;]+)",
            re.IGNORECASE,
        ),

        "occupancy_type": re.compile(
            r"\boccupancy\b\s*[:=]\s*([^\n;]+)",
            re.IGNORECASE,
        ),

        "requested_height": re.compile(
            r"\bproposed\s+height\b\s*[:=]\s*([^\n;]+)",
            re.IGNORECASE,
        ),

        "requested_floors": re.compile(
            r"\bproposed\s+(?:number\s+of\s+)?floors?\b"
            r"\s*[:=]\s*([0-9]+)",
            re.IGNORECASE,
        ),

        "floor_height": re.compile(
            r"\bfloor\s+height\b\s*[:=]\s*"
            r"([0-9]+(?:\.[0-9]+)?)",
            re.IGNORECASE,
        ),
    }

    def map(
        self,
        facts: Any,
        evidence: Any,
    ) -> VisionPlanningMapResult:

        result = VisionPlanningMapResult(
            facts=facts
        )

        observations = getattr(
            evidence,
            "observations",
            [],
        )

        for observation in observations:

            observation_type = str(
                getattr(
                    observation,
                    "observation_type",
                    "",
                )
            ).strip().lower()

            value = getattr(
                observation,
                "value",
                None,
            )

            text = getattr(
                observation,
                "text",
                None,
            )

            confidence = float(
                getattr(
                    observation,
                    "confidence",
                    0.0,
                )
                or 0.0
            )

            if confidence <= 0:
                continue

            # ---------------------------------------------------------
            # DIRECT SITE FACTS
            # ---------------------------------------------------------

            field_name = self.SITE_FIELD_MAP.get(
                observation_type
            )

            if field_name is not None:

                if self._set_fact(
                    facts,
                    field_name,
                    value,
                    source="vision_image",
                    evidence=text or value,
                    result=result,
                ):
                    continue

            # ---------------------------------------------------------
            # PLOT AREA
            # ---------------------------------------------------------

            if observation_type == "plot_area":

                if self._set_fact(
                    facts,
                    "plot_area",
                    value,
                    source="vision_image",
                    evidence=text or value,
                    result=result,
                ):
                    continue

            # ---------------------------------------------------------
            # ROAD
            # ---------------------------------------------------------

            if observation_type == "road":

                self._map_road(
                    facts,
                    value,
                    text,
                    result,
                )

                continue

            # ---------------------------------------------------------
            # DIMENSIONS
            # ---------------------------------------------------------

            if observation_type == "dimension":

                self._map_dimension(
                    facts,
                    value,
                    text,
                    result,
                )

                continue

            # ---------------------------------------------------------
            # PLOT BOUNDARY
            # ---------------------------------------------------------

            if observation_type == "plot_boundary":

                self._set_fact(
                    facts,
                    "boundary",
                    value,
                    source="vision_image",
                    evidence=text or value,
                    result=result,
                )

                continue

            # ---------------------------------------------------------
            # IMAGE REGULATORY INFORMATION
            # ---------------------------------------------------------

            combined_text = self._combined_text(
                text,
                value,
            )

            if combined_text:

                regulatory = self._extract_regulatory_value(
                    combined_text
                )

                if regulatory:

                    field_name, field_value = regulatory

                    self._set_fact(
                        facts,
                        field_name,
                        field_value,
                        source="vision_image",
                        evidence=combined_text,
                        result=result,
                    )

                    if field_name not in result.image_regulatory_fields:
                        result.image_regulatory_fields.append(
                            field_name
                        )

                    continue

                # -----------------------------------------------------
                # PROJECT / USER REQUIREMENT INFORMATION
                # -----------------------------------------------------

                project = self._extract_project_value(
                    combined_text
                )

                if project:

                    field_name, field_value = project

                    self._set_fact(
                        facts,
                        field_name,
                        field_value,
                        source="vision_image",
                        evidence=combined_text,
                        result=result,
                    )

                    if field_name not in result.image_project_fields:
                        result.image_project_fields.append(
                            field_name
                        )

                    continue

                # -----------------------------------------------------
                # KEEP REGULATORY-LOOKING TEXT AS EVIDENCE
                # -----------------------------------------------------

                if self._looks_regulatory(
                    combined_text
                ):
                    result.ignored_regulatory_text.append(
                        combined_text
                    )

        return result

    def _map_road(
        self,
        facts: Any,
        value: Any,
        text: str | None,
        result: VisionPlanningMapResult,
    ) -> None:

        if isinstance(value, dict):

            width = value.get("width")
            name = value.get("name")

            if width is not None:
                self._set_fact(
                    facts,
                    "road_width",
                    width,
                    source="vision_image",
                    evidence=text or value,
                    result=result,
                )

            if name:
                self._set_fact(
                    facts,
                    "road_name",
                    name,
                    source="vision_image",
                    evidence=text or value,
                    result=result,
                )

        elif isinstance(value, (int, float)):

            self._set_fact(
                facts,
                "road_width",
                value,
                source="vision_image",
                evidence=text or value,
                result=result,
            )

    def _map_dimension(
        self,
        facts: Any,
        value: Any,
        text: str | None,
        result: VisionPlanningMapResult,
    ) -> None:

        if not isinstance(value, (int, float)):
            return

        dimensions = getattr(
            facts,
            "plot_side_lengths",
            None,
        )

        if not isinstance(dimensions, dict):
            dimensions = {}

        key = f"dimension_{len(dimensions) + 1}"

        dimensions[key] = float(value)

        self._set_fact(
            facts,
            "plot_side_lengths",
            dimensions,
            source="vision_image",
            evidence=text or value,
            result=result,
        )

    def _extract_regulatory_value(
        self,
        text: str,
    ) -> tuple[str, Any] | None:

        for field_name, patterns in (
            self.IMAGE_REGULATORY_PATTERNS.items()
        ):

            for pattern in patterns:

                match = pattern.search(text)

                if not match:
                    continue

                raw_value = match.group(1)

                try:
                    numeric_value = float(
                        raw_value
                    )
                except ValueError:
                    continue

                if field_name == "setback":
                    return (
                        "setback",
                        numeric_value,
                    )

                if field_name == "margin":
                    return (
                        "margin",
                        numeric_value,
                    )

                return (
                    field_name,
                    numeric_value,
                )

        return None

    def _extract_project_value(
        self,
        text: str,
    ) -> tuple[str, Any] | None:

        for field_name, pattern in (
            self.PROJECT_PATTERNS.items()
        ):

            match = pattern.search(text)

            if not match:
                continue

            value = match.group(1).strip()

            if field_name == "requested_floors":

                try:
                    return (
                        field_name,
                        int(value),
                    )
                except ValueError:
                    continue

            if field_name == "floor_height":

                try:
                    return (
                        field_name,
                        float(value),
                    )
                except ValueError:
                    continue

            return (
                field_name,
                value,
            )

        return None

    @staticmethod
    def _combined_text(
        text: Any,
        value: Any,
    ) -> str:

        parts = []

        if text:
            parts.append(str(text))

        if value is not None:

            if isinstance(value, dict):
                for key, val in value.items():
                    parts.append(
                        f"{key}: {val}"
                    )
            else:
                parts.append(str(value))

        return " ".join(parts).strip()

    @staticmethod
    def _looks_regulatory(
        text: str,
    ) -> bool:

        keywords = (
            "fsi",
            "setback",
            "margin",
            "parking requirement",
            "fire norm",
            "fire requirement",
            "permissible height",
            "permissible floor",
            "tdr",
            "premium",
            "amenity",
            "open space",
            "road widening",
            "reservation",
        )

        lower = text.lower()

        return any(
            keyword in lower
            for keyword in keywords
        )

    @staticmethod
    def _set_fact(
        facts: Any,
        field_name: str,
        value: Any,
        *,
        source: str,
        evidence: Any,
        result: VisionPlanningMapResult,
    ) -> bool:

        if value is None:
            return False

        try:

            if hasattr(
                facts,
                field_name,
            ):
                setattr(
                    facts,
                    field_name,
                    value,
                )

            else:

                values = getattr(
                    facts,
                    "values",
                    None,
                )

                if not isinstance(
                    values,
                    dict,
                ):
                    return False

                values[field_name] = value

            # Provenance
            fact_sources = getattr(
                facts,
                "fact_sources",
                None,
            )

            if isinstance(
                fact_sources,
                dict,
            ):
                fact_sources[field_name] = source

            fact_confidence = getattr(
                facts,
                "fact_confidence",
                None,
            )

            if isinstance(
                fact_confidence,
                dict,
            ):
                fact_confidence[field_name] = 1.0

            fact_evidence = getattr(
                facts,
                "fact_evidence",
                None,
            )

            if isinstance(
                fact_evidence,
                dict,
            ):
                fact_evidence[field_name] = evidence

            if field_name not in result.mapped_fields:
                result.mapped_fields.append(
                    field_name
                )

            result.evidence[field_name] = {
                "source": source,
                "value": value,
                "evidence": evidence,
            }

            return True

        except Exception:
            return False
