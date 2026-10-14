"""
Vision-specific multimodal AI client.

This client is intentionally separate from the application's
general-purpose townplanning.ai GPTClient.

It supports image analysis through the OpenAI Responses API.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from openai import OpenAI

from townplanning.core.settings import get_settings


class VisionAIClient:
    """
    Dedicated multimodal AI client for Vision.

    This class does NOT modify or replace the application's
    general-purpose GPTClient.
    """

    def __init__(
        self,
        client: Any | None = None,
    ) -> None:

        settings = get_settings()

        self.client = client or OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

        self.model = settings.OPENAI_MODEL

    # ======================================================
    # IMAGE ANALYSIS
    # ======================================================

    def analyze_image(
        self,
        image_path: str | Path,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        image_path = Path(
            image_path
        )

        if not image_path.exists():
            raise FileNotFoundError(
                image_path
            )

        if not image_path.is_file():
            raise ValueError(
                f"Not a file: {image_path}"
            )

        image_data = self._encode_image(
            image_path
        )

        mime_type = self._detect_mime_type(
            image_data
        )

        image_url = (
            f"data:{mime_type};base64,"
            f"{image_data}"
        )

        # --------------------------------------------------
        # Multimodal Responses API request
        #
        # IMPORTANT:
        # Do not pass temperature here.
        #
        # The configured GPT model does not support the
        # temperature parameter.
        # --------------------------------------------------

        response = self.client.responses.create(

            model=self.model,

            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": system_prompt,
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": user_prompt,
                        },
                        {
                            "type": "input_image",
                            "image_url": image_url,
                        },
                    ],
                },
            ],

            text={
                "format": {
                    "type": "json_object",
                }
            },
        )

        return response.output_text

    # ======================================================
    # IMAGE ENCODING
    # ======================================================

    @staticmethod
    def _encode_image(
        image_path: Path,
    ) -> str:

        data = image_path.read_bytes()

        if not data:
            raise ValueError(
                f"Image is empty: {image_path}"
            )

        return base64.b64encode(
            data
        ).decode(
            "utf-8"
        )

    # ======================================================
    # MIME DETECTION
    # ======================================================

    @staticmethod
    def _detect_mime_type(
        base64_data: str,
    ) -> str:

        try:

            data = base64.b64decode(
                base64_data,
                validate=True,
            )

        except Exception as exc:

            raise ValueError(
                "Invalid base64 image data."
            ) from exc

        # PNG
        if data.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            return "image/png"

        # JPEG
        if data.startswith(
            b"\xff\xd8\xff"
        ):
            return "image/jpeg"

        # GIF
        if (
            data.startswith(b"GIF87a")
            or data.startswith(b"GIF89a")
        ):
            return "image/gif"

        # WEBP
        if (
            data.startswith(b"RIFF")
            and len(data) >= 12
            and data[8:12] == b"WEBP"
        ):
            return "image/webp"

        # BMP
        if data.startswith(
            b"BM"
        ):
            return "image/bmp"

        raise ValueError(
            "Unsupported image format. "
            "Supported formats: "
            "PNG, JPEG, GIF, WEBP and BMP."
        )