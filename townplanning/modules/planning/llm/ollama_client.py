from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path
from typing import Any


class OllamaClient:
    """
    Minimal Ollama HTTP client.

    Supports:
        1. normal text generation
        2. multimodal generation with images

    Ollama is used as an extraction/reasoning assistant.
    It is NOT the authority for UDCPR regulatory values.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "gemma3:12b",
        timeout: int = 600,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    # ==========================================================
    # TEXT GENERATION
    # ==========================================================

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
    ) -> str:

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
            },
        }

        return self._post(payload)

    # ==========================================================
    # MULTIMODAL GENERATION
    # ==========================================================

    def generate_with_images(
        self,
        prompt: str,
        images: list[str] | None = None,
        *,
        temperature: float = 0.0,
    ) -> str:
        """
        Send text + images to a vision-capable Ollama model.

        `images` contains filesystem paths.

        Images are converted to base64 because Ollama's
        /api/generate endpoint expects base64 image data.
        """

        encoded_images: list[str] = []

        for image_path in images or []:
            path = Path(image_path)

            if not path.exists():
                raise FileNotFoundError(
                    f"Planning image does not exist: {path}"
                )

            if not path.is_file():
                raise ValueError(
                    f"Planning image is not a file: {path}"
                )

            encoded_images.append(
                base64.b64encode(
                    path.read_bytes()
                ).decode("ascii")
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
            },
        }

        if encoded_images:
            payload["images"] = encoded_images

        return self._post(payload)

    # ==========================================================
    # HTTP
    # ==========================================================

    def _post(
        self,
        payload: dict[str, Any],
    ) -> str:

        data = json.dumps(
            payload
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                body = (
                    response
                    .read()
                    .decode("utf-8")
                )

        except Exception as exc:
            raise RuntimeError(
                f"Ollama request failed: {exc}"
            ) from exc

        try:
            result = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Ollama returned invalid JSON response."
            ) from exc

        response_text = result.get(
            "response",
            "",
        )

        if not response_text:
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        return str(response_text)
