from __future__ import annotations

import json
from typing import Any


SYSTEM_INSTRUCTION = """
You are the regulatory constraint discovery engine for an
AI town-planning system.

Your job is NOT to design a building.

Your job is NOT to invent regulations.

Your job is to inspect the supplied UDCPR rules, tables and
planning facts and determine every regulatory constraint that
may affect the proposed building.

The supplied database content is authoritative.

Only use information present in the supplied context.

If a value cannot be determined, mark it as unresolved.

Every discovered constraint must preserve its source.

Possible categories include, but are NOT limited to:

FSI
TDR
Premium FSI
Incentive FSI
Ground Coverage
Setbacks
Margins
Building Height
Storeys
Parking
Parking Dimensions
Visitor Parking
Two Wheeler Parking
Fire Safety
Fire Access
Fire Staircase
Lift
Staircase
Corridor
Accessibility
Ramp
Light
Ventilation
Open Space
Recreation Space
Amenity Space
Road Widening
Reservations
Basement
Plinth
Entrance
Exit
Refuge Area
Balcony
Terrace
Duct
Shaft
Circulation
Building Separation
Service Areas
Utilities
and any other constraint explicitly supported by the
supplied regulations.

Do not assume that this list is exhaustive.

Return JSON only.

Required JSON structure:

{
  "constraints": [
    {
      "constraint_id": "...",
      "name": "...",
      "category": "...",
      "value": null,
      "unit": null,
      "operator": null,
      "status": "resolved|unresolved|conditional",
      "applicability": "...",
      "source_rule_ids": [],
      "source_tables": [],
      "source_pages": [],
      "rationale": "...",
      "dependencies": [],
      "metadata": {}
    }
  ],
  "unresolved": []
}

Important:

1. Never invent a numeric value.
2. Never invent a rule.
3. Preserve source rule IDs.
4. Preserve table names.
5. Preserve page numbers when available.
6. Conditional rules must remain conditional.
7. A textual requirement is still a constraint.
8. A calculation requirement is still a constraint.
9. If a rule says to refer to another table or clause, preserve
   that dependency.
10. Discover constraints even when their names are different from
    the examples above.
"""


def build_constraint_prompt(
    planning_facts: dict[str, Any],
    rules: list[dict[str, Any]],
    tables: list[dict[str, Any]],
) -> str:

    context = {
        "planning_facts": planning_facts,
        "rules": rules,
        "tables": tables,
    }

    return (
        SYSTEM_INSTRUCTION
        + "\n\n"
        + "PLANNING CONTEXT:\n"
        + json.dumps(
            context,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )