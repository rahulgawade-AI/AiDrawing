from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from townplanning.ai.factory import AIClientFactory
from townplanning.ai.image_utils import encode_image
from townplanning.ai.models import AIRequest


@dataclass(slots=True)
class AIPlotCandidate:
    """
    AI-proposed plot boundary.

    Coordinates are normalized to a 0..1000 image coordinate system.

    IMPORTANT:
    This is only a candidate. It is never treated as authoritative
    geometry until validated by the hybrid plot detector.
    """

    points: list[tuple[float, float]]
    confidence: float
    reasoning: str | None = None


class AIPlotDetector:
    """
    Vision-AI assisted plot boundary detector.

    Uses the existing AIClientFactory, therefore the configured
    Ollama/OpenAI provider is reused.

    The AI is NOT allowed to:
        - calculate FSI
        - calculate setbacks
        - determine permissible height
        - determine parking
        - invent plot dimensions
        - invent regulatory facts

    It only identifies the visual location of the land parcel.
    """

    SYSTEM_PROMPT = """
You are an expert land-survey, cadastral-map and site-plan
image analyzer.

Your ONLY task is to identify the boundary of the PRIMARY LAND
PLOT / PARCEL that is the subject of the drawing.

The image may be any of the following:

- CAD site plan
- scanned survey drawing
- municipal site plan
- hand-drawn plan
- architectural site plan
- satellite/map image
- photograph of a plan
- PDF page converted to an image
- colored presentation drawing
- technical drawing

You must distinguish the plot boundary from:

- page borders
- image borders
- title blocks
- text boxes
- buildings
- building footprints
- roads
- dimension lines
- north arrows
- neighboring plots
- compound walls when they are clearly not the subject plot
- decorative graphics
- legends

Return ONLY valid JSON.

Required structure:

{
    "plot_found": true,
    "polygon": [
        [x, y],
        [x, y],
        [x, y]
    ],
    "confidence": 0.0,
    "reasoning": "short visual explanation"
}

Coordinates MUST be normalized to 0..1000:

x = horizontal position from left to right
y = vertical position from top to bottom

Rules:

1. polygon must contain at least 3 points.
2. polygon should follow the visible plot boundary.
3. Do not return the page/image border.
4. Do not return a building footprint.
5. Do not return a road boundary.
6. Do not invent missing geometry.
7. If the plot boundary cannot be identified with reasonable confidence,
   return:

{
    "plot_found": false,
    "polygon": [],
    "confidence": 0.0,
    "reasoning": "..."
}

8. confidence must be between 0 and 1.
9. Do not calculate plot area.
10. Do not calculate FSI.
11. Do not calculate setbacks.
12. Do not calculate road width.
13. Do not infer regulatory information.
14. Return JSON only.
"""

    USER_PROMPT = """
Analyze the supplied drawing image.

Identify the PRIMARY LAND PLOT / PARCEL.

Look for visual evidence such as:

- a closed parcel boundary
- cadastral boundary
- survey boundary
- plot outline
- labels such as Plot, Plot No, S.No., Survey No., CTS
- plot-area text
- dimensions associated with the parcel
- roads immediately adjacent to the parcel

The plot may be irregular.

Do not assume that the largest polygon is the plot.

Do not select the page border.

Do not select a building footprint.

Do not select a title block.

Return only the JSON structure requested by the system prompt.
"""

    def __init__(
        self,
        client: Any | None = None,
    ) -> None:
        self.client = client or AIClientFactory.create()

    def detect(
        self,
        image_path: str | Path,
    ) -> AIPlotCandidate | None:
        """
        Ask the configured vision model for a plot candidate.

        Failure is deliberately converted to None so the classical
        detector can continue working.
        """

        image_path = Path(image_path)

        image = encode_image(image_path)

        request = AIRequest(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=self.USER_PROMPT,
            temperature=0.0,
            response_format="json",
            images=[image],
        )

        try:
            response = self.client.generate(request)
        except Exception as exc:
            print(
                "[PLOT AI] request failed:",
                exc,
            )
            return None

        if not response.success:
            print(
                "[PLOT AI] provider failed:",
                response.error,
            )
            return None

        try:
            data = self._parse_json(
                response.content
            )
        except Exception as exc:
            print(
                "[PLOT AI] invalid JSON:",
                exc,
            )
            return None

        return self._parse_candidate(data)

    # ==========================================================
    # JSON
    # ==========================================================

    @staticmethod
    def _parse_json(
        content: str,
    ) -> dict[str, Any]:
        content = str(
            content or ""
        ).strip()

        if not content:
            raise ValueError(
                "Empty AI response."
            )

        try:
            value = json.loads(content)

            if isinstance(value, dict):
                return value

        except json.JSONDecodeError:
            pass

        # Some models still add markdown fences even when JSON
        # response format is requested.
        match = re.search(
            r"\{.*\}",
            content,
            re.DOTALL,
        )

        if match:
            value = json.loads(
                match.group(0)
            )

            if isinstance(value, dict):
                return value

        raise ValueError(
            "AI returned invalid JSON."
        )

    # ==========================================================
    # CANDIDATE
    # ==========================================================

    @classmethod
    def _parse_candidate(
        cls,
        data: dict[str, Any],
    ) -> AIPlotCandidate | None:
        found = data.get(
            "plot_found",
            False,
        )

        if not bool(found):
            return None

        polygon = data.get(
            "polygon",
            [],
        )

        if not isinstance(
            polygon,
            list,
        ):
            return None

        points: list[
            tuple[float, float]
        ] = []

        for item in polygon:
            if not isinstance(
                item,
                (list, tuple),
            ):
                continue

            if len(item) < 2:
                continue

            try:
                x = float(item[0])
                y = float(item[1])
            except (
                TypeError,
                ValueError,
            ):
                continue

            if not (
                math.isfinite(x)
                and math.isfinite(y)
            ):
                continue

            # Normalized coordinates are mandatory.
            if x < 0.0 or x > 1000.0:
                continue

            if y < 0.0 or y > 1000.0:
                continue

            points.append(
                (x, y)
            )

        if len(points) < 3:
            return None

        try:
            confidence = float(
                data.get(
                    "confidence",
                    0.0,
                )
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

        reasoning = data.get(
            "reasoning"
        )

        if reasoning is not None:
            reasoning = str(
                reasoning
            )

        return AIPlotCandidate(
            points=points,
            confidence=confidence,
            reasoning=reasoning,
        )