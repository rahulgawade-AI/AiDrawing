"""
AI request/response models.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIRequest:
    """
    Generic request to an AI provider.

    For text-only requests:
        images=[]

    For vision requests:
        images contains base64-encoded image data.
    """

    system_prompt: str

    user_prompt: str

    temperature: float = 0.0

    response_format: str = "json"

    images: list[str] = field(
        default_factory=list
    )


@dataclass(slots=True)
class AIResponse:
    """
    Normalized AI response.
    """

    success: bool

    content: str

    raw_response: Any

    error: str | None = None