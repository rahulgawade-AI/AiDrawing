"""
Utilities for converting structured objects into readable text.
"""

from __future__ import annotations

import json
from typing import Any


class TextFormatter:

    @staticmethod
    def format(value: Any, indent: int = 0) -> str:
        """Convert Python objects into readable text."""

        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, (int, float, bool)):
            return str(value)

        if isinstance(value, list):

            lines = []

            for item in value:

                text = TextFormatter.format(item, indent)

                if text:
                    lines.append(text)

            return "\n".join(lines)

        if isinstance(value, dict):

            # Common engineering definition structure
            if set(value.keys()) >= {"term", "definition"}:
                return f"{value['term']}: {value['definition']}"

            # Common engineering measurement
            if {"name", "value"} <= set(value.keys()):
                return f"{value['name']}: {value['value']}"

            lines = []

            for k, v in value.items():

                text = TextFormatter.format(v, indent + 2)

                if text:
                    lines.append(f"{k}: {text}")

            return "\n".join(lines)

        return json.dumps(value, ensure_ascii=False, default=str)