from __future__ import annotations

import json
import re
from pathlib import Path

from townplanning.ai.factory import AIClientFactory
from townplanning.ai.image_utils import encode_image
from townplanning.ai.models import AIRequest

from .schemas import AIRoadResult


class AIRoadDetector:
    """
    AI-assisted road detector.

    Uses the existing AIClientFactory and therefore
    automatically uses the configured provider:

        Ollama
        or
        OpenAI

    No new AI client is created here.
    """

    SYSTEM_PROMPT = """
You are an expert site-plan and town-planning drawing
vision analyzer.

Analyze the supplied site-plan image and identify roads
that are visible in or immediately adjacent to the plot.

Return ONLY valid JSON.

Required JSON structure:

{
    "roads": [
        {
            "road_visible": true,
            "road_location": "south",
            "road_label": "D.P. Road",
            "approximate_width": 18.0,
            "unit": "m",
            "confidence": 0.95
        }
    ]
}

If no road is visible:

{
    "roads": []
}

Rules:

1. Do not invent a road.
2. Only report a road if visual evidence exists.
3. road_location must preferably be one of:
   north
   south
   east
   west
   north-east
   north-west
   south-east
   south-west
   inside
   unknown

4. approximate_width must be numeric when a road width
   can reasonably be determined.

5. If width cannot be determined, use null.

6. confidence must be between 0 and 1.

7. Return JSON only.
"""

    USER_PROMPT = """
Analyze this site plan.

Identify all roads visible in or immediately adjacent
to the plot.

For each road determine:

- whether it is actually a road
- location relative to the plot
- road label/name if visible
- approximate road width
- unit
- confidence

Do not confuse plot boundaries, dimension lines,
building boundaries, or drawing borders with roads.
"""

    def __init__(self):

        self.client = AIClientFactory.create()

    def detect(
        self,
        image_path: str | Path,
    ) -> list[AIRoadResult]:

        image = encode_image(image_path)

        request = AIRequest(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=self.USER_PROMPT,
            temperature=0.0,
            response_format="json",
            images=[image],
        )

        response = self.client.generate(request)

        if not response.success:
            raise RuntimeError(
                f"AI road detection failed: "
                f"{response.error}"
            )

        data = self._parse_json(
            response.content
        )

        return self._parse_roads(data)

    # --------------------------------------------------
    # JSON parsing
    # --------------------------------------------------

    @staticmethod
    def _parse_json(
        content: str,
    ) -> dict:

        content = content.strip()

        #
        # First try direct JSON.
        #
        try:
            data = json.loads(content)

            if isinstance(data, dict):
                return data

        except json.JSONDecodeError:
            pass

        #
        # Some models occasionally wrap JSON in
        # markdown fences despite the JSON format.
        #
        match = re.search(
            r"\{.*\}",
            content,
            re.DOTALL,
        )

        if match:

            try:

                data = json.loads(
                    match.group(0)
                )

                if isinstance(data, dict):
                    return data

            except json.JSONDecodeError:
                pass

        raise ValueError(
            "Ollama returned invalid JSON:\n"
            f"{content}"
        )

    # --------------------------------------------------
    # Road parsing
    # --------------------------------------------------

    @staticmethod
    def _parse_roads(
        data: dict,
    ) -> list[AIRoadResult]:

        roads_data = data.get(
            "roads",
            [],
        )

        if not isinstance(
            roads_data,
            list,
        ):
            return []

        roads: list[AIRoadResult] = []

        for item in roads_data:

            if not isinstance(
                item,
                dict,
            ):
                continue

            visible = bool(
                item.get(
                    "road_visible",
                    True,
                )
            )

            if not visible:
                continue

            width = item.get(
                "approximate_width"
            )

            #
            # Normalize width.
            #
            if isinstance(
                width,
                str,
            ):

                match = re.search(
                    r"\d+(?:\.\d+)?",
                    width,
                )

                width = (
                    float(match.group())
                    if match
                    else None
                )

            elif isinstance(
                width,
                (int, float),
            ):

                width = float(width)

            else:

                width = None

            confidence = item.get(
                "confidence",
                0.0,
            )

            try:
                confidence = float(
                    confidence
                )
            except (
                TypeError,
                ValueError,
            ):
                confidence = 0.0

            confidence = max(
                0.0,
                min(
                    1.0,
                    confidence,
                ),
            )

            roads.append(
                AIRoadResult(
                    road_visible=True,
                    road_location=(
                        item.get(
                            "road_location"
                        )
                    ),
                    road_label=(
                        item.get(
                            "road_label"
                        )
                    ),
                    approximate_width=width,
                    unit=(
                        item.get(
                            "unit",
                            "m",
                        )
                    ),
                    confidence=confidence,
                    raw_response=item,
                )
            )

        return roads
