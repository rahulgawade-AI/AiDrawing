"""
General-purpose Vision AI analyzer.

This module is Vision-specific and intentionally does not use or modify
the shared townplanning.ai GPT client.

Responsibilities:
    Image
      ↓
    Vision AI
      ↓
    Visual observations
      ↓
    VisionEvidence

This module performs perception only.

It MUST NOT:
    - calculate FSI
    - calculate permissible FSI
    - calculate setbacks
    - calculate margins
    - calculate parking requirements
    - determine fire requirements
    - determine permissible building height
    - determine permissible floors
    - determine UDCPR compliance
    - make regulatory decisions
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from townplanning.modules.vision.ai.vision_ai_client import VisionAIClient
from townplanning.modules.vision.domain.vision_observation import (
    VisionEvidence,
    VisionObservation,
)


class VisionAnalyzer:
    """
    Vision-specific multimodal analyzer.

    It accepts arbitrary image types, including:

        - photographs
        - handwritten sketches
        - hand-drawn site plans
        - survey plans
        - layout plans
        - floor plans
        - building plans
        - CAD screenshots
        - satellite images
        - aerial images
        - maps
        - scanned documents
        - mixed images

    The result is evidence, not PlanningFacts.
    """

    SYSTEM_PROMPT = """
You are a professional visual-analysis engine for a town-planning
application.

Analyze the supplied image itself.

The image may be ANY of the following:

- normal photograph
- handwritten sketch
- hand-drawn site plan
- survey drawing
- technical site plan
- layout plan
- floor plan
- building plan
- CAD drawing or CAD screenshot
- satellite image
- aerial image
- map
- scanned document
- planning document
- mixed visual content
- unknown image type

Your task is VISUAL PERCEPTION ONLY.

Identify what is actually visible in the image.

Do NOT calculate, infer, or decide:

- FSI
- permissible FSI
- basic FSI
- premium FSI
- TDR
- setbacks
- margins
- required setbacks
- parking requirements
- fire requirements
- permissible building height
- permissible number of floors
- lift requirements
- staircase requirements
- amenity requirements
- recreational open space requirements
- development permissions
- zoning permissions
- UDCPR compliance
- regulatory eligibility

Do not invent information that is not visually supported.

If information is uncertain, report the uncertainty using a lower
confidence value.

Extract visible text when useful.

For geometry, report only geometry that can reasonably be observed
from the image.

Bounding boxes must be normalized to a 0..1000 coordinate system:

x1, y1, x2, y2

where:

- 0,0 = top-left
- 1000,1000 = bottom-right

Return ONLY valid JSON.

JSON structure:

{
  "image_type": "string",
  "image_type_confidence": 0.0,
  "description": "short visual description",
  "observations": [
    {
      "type": "string",
      "value": null,
      "unit": null,
      "text": null,
      "confidence": 0.0,
      "bbox": null
    }
  ]
}

Allowed observation types include:

- plot
- plot_boundary
- plot_area
- plot_number
- survey_number
- cts_number
- road
- road_width
- road_name
- building
- building_footprint
- room
- wall
- door
- window
- stair
- lift
- dimension
- scale
- north
- tree
- waterbody
- parking
- vehicle
- person
- text
- label
- symbol
- structure
- document
- map_feature
- unknown

For dimensions:

{
  "type": "dimension",
  "value": 22.30,
  "unit": "m",
  "text": "22.30",
  "confidence": 0.95,
  "bbox": [x1, y1, x2, y2]
}

For a road:

{
  "type": "road",
  "value": {
    "width": 12.0,
    "name": "ROAD"
  },
  "unit": "m",
  "text": "12.00 M WIDE ROAD",
  "confidence": 0.95,
  "bbox": [x1, y1, x2, y2]
}

For plot area:

{
  "type": "plot_area",
  "value": 745.60,
  "unit": "sq.m.",
  "text": "745.60 SQ.M.",
  "confidence": 0.98,
  "bbox": [x1, y1, x2, y2]
}

For plot number:

{
  "type": "plot_number",
  "value": "78/5",
  "unit": null,
  "text": "S.NO. 78/5",
  "confidence": 0.98,
  "bbox": [x1, y1, x2, y2]
}

Do not turn a textual regulatory statement into a regulatory
conclusion.

For example, if the image contains a table saying:

"PERMISSIBLE FSI 2.0"

you may report the visible text as a text observation, but you must
NOT treat it as an authoritative FSI rule or calculate anything from
it.

Similarly, if a drawing says:

"PROPOSED G+5"

report that as visible text or a proposed-building observation.
Do not decide whether G+5 is permissible.

Preserve visible numbers and units accurately.
"""

    USER_PROMPT = """
Analyze this image as a visual-perception task.

Identify:

1. The overall image/document type.
2. Visible textual information.
3. Visible plot or parcel boundaries.
4. Roads and visible road widths.
5. Buildings and building footprints.
6. Rooms, walls, doors, windows, stairs and lifts where visible.
7. Dimensions and units.
8. Scale information.
9. North arrow/direction.
10. Parking/vehicles where visibly represented.
11. Trees, water bodies and other visible site features.
12. Survey/plot/CTS numbers where visible.
13. Any other useful visual features.

Do not perform regulatory calculations or compliance decisions.

Return only the requested JSON.
"""

    def __init__(
        self,
        client: VisionAIClient | None = None,
    ) -> None:
        self.client = client or VisionAIClient()

    def analyze(
        self,
        image_path: str | Path,
    ) -> VisionEvidence:
        """
        Analyze one arbitrary image and return structured visual evidence.
        """

        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(image_path)

        if not image_path.is_file():
            raise ValueError(f"Not a file: {image_path}")

        raw = self.client.analyze_image(
            image_path=image_path,
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=self.USER_PROMPT,
        )

        data = self._parse_json(raw)

        evidence = VisionEvidence(
            image_type=str(
                data.get("image_type", "unknown")
            ),
            image_type_confidence=self._float(
                data.get(
                    "image_type_confidence",
                    data.get("confidence", 0.0),
                )
            ),
        )

        description = data.get("description")

        if description:
            evidence.metadata["description"] = str(description)

        observations = data.get("observations", [])

        if not isinstance(observations, list):
            observations = []

        for item in observations:
            if not isinstance(item, dict):
                continue

            observation = self._observation_from_dict(item)

            if observation is not None:
                evidence.add(observation)

        return evidence

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """
        Parse JSON returned by the Vision AI model.

        Handles occasional markdown fences defensively.
        """

        if not raw:
            raise ValueError("Vision AI returned an empty response.")

        text = raw.strip()

        if text.startswith("```"):
            lines = text.splitlines()

            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Vision AI returned invalid JSON: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "Vision AI JSON root must be an object."
            )

        return data

    @classmethod
    def _observation_from_dict(
        cls,
        item: dict[str, Any],
    ) -> VisionObservation | None:
        observation_type = item.get("type")

        if not observation_type:
            return None

        observation_type = str(observation_type).strip()

        if not observation_type:
            return None

        confidence = cls._float(
            item.get("confidence", 0.0)
        )

        bbox = cls._bbox(item.get("bbox"))

        value = item.get("value")

        unit = item.get("unit")

        if unit is not None:
            unit = str(unit)

        text = item.get("text")

        if text is not None:
            text = str(text)

        metadata: dict[str, Any] = {}

        if "value" in item and isinstance(
            item["value"],
            dict,
        ):
            metadata["structured_value"] = item["value"]

        return VisionObservation(
            observation_type=observation_type,
            value=value,
            confidence=confidence,
            source="vision_ai",
            source_detail="openai_multimodal",
            unit=unit,
            bbox=bbox,
            text=text,
            metadata=metadata,
        )

    @staticmethod
    def _float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _bbox(
        cls,
        value: Any,
    ) -> tuple[float, float, float, float] | None:
        if value is None:
            return None

        if not isinstance(value, (list, tuple)):
            return None

        if len(value) != 4:
            return None

        try:
            values = [
                max(
                    0.0,
                    min(
                        1000.0,
                        float(x),
                    ),
                )
                for x in value
            ]
        except (TypeError, ValueError):
            return None

        x1, y1, x2, y2 = values

        if x2 < x1:
            x1, x2 = x2, x1

        if y2 < y1:
            y1, y2 = y2, y1

        return (
            x1,
            y1,
            x2,
            y2,
        )