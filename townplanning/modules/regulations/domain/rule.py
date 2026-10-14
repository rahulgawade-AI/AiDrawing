"""
Machine-readable engineering rule.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class Rule:

    id: str

    regulation_id: str

    category: str

    name: str

    description: str

    condition: dict = field(default_factory=dict)

    result: dict = field(default_factory=dict)

    priority: int = 1

    enabled: bool = True

    metadata: dict = field(default_factory=dict)