"""
Planning requirement collector.

Determines which USER / PROJECT requirements are missing.

This does NOT determine regulatory requirements.

Regulatory requirements are handled by the existing
PlanningInputGate and UDCPR rule system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlanningUserQuestion:
    field: str
    question: str
    required: bool = True
    options: list[str] = field(
        default_factory=list
    )


@dataclass(slots=True)
class PlanningRequirementResult:
    missing: list[PlanningUserQuestion] = field(
        default_factory=list
    )

    complete: bool = False


class PlanningRequirementCollector:
    """
    Collects project requirements that cannot normally be obtained
    from UDCPR.

    Examples:

        - residential/commercial/mixed use
        - BHK mix
        - unit areas
        - number of units
        - requested floors
        - parking preference
        - design objectives
    """

    def evaluate(
        self,
        facts: Any,
    ) -> PlanningRequirementResult:

        missing: list[PlanningUserQuestion] = []

        building_use = self._first_value(
            facts,
            "building_use",
        )

        if not building_use:

            missing.append(
                PlanningUserQuestion(
                    field="building_use",
                    question=(
                        "What is the proposed building use?"
                    ),
                    options=[
                        "Residential",
                        "Commercial",
                        "Mixed-use",
                    ],
                )
            )

            return PlanningRequirementResult(
                missing=missing,
                complete=False,
            )

        normalized_use = str(
            building_use
        ).lower()

        if "residential" in normalized_use:

            self._require(
                facts,
                missing,
                "requested_units",
                (
                    "How many residential units are required "
                    "in total?"
                ),
            )

            requested_mix = self._first_value(
                facts,
                "requested_unit_mix",
            )

            if not requested_mix:

                missing.append(
                    PlanningUserQuestion(
                        field="requested_unit_mix",
                        question=(
                            "What BHK mix do you require? "
                            "For example: 2 BHK = 8 units, "
                            "3 BHK = 4 units."
                        ),
                    )
                )

            self._require(
                facts,
                missing,
                "requested_unit_area",
                (
                    "What approximate carpet area do you "
                    "want for each BHK type?"
                ),
            )

        elif "mixed" in normalized_use:

            self._require(
                facts,
                missing,
                "residential_component",
                (
                    "What residential component is required "
                    "in the mixed-use project?"
                ),
            )

            self._require(
                facts,
                missing,
                "commercial_component",
                (
                    "What commercial component is required "
                    "in the mixed-use project?"
                ),
            )

        elif "commercial" in normalized_use:

            self._require(
                facts,
                missing,
                "commercial_use",
                (
                    "What type of commercial use is proposed?"
                ),
            )

        # Requested floors are a project requirement, not a
        # regulatory determination.
        if not self._first_value(
            facts,
            "requested_floors",
        ):
            missing.append(
                PlanningUserQuestion(
                    field="requested_floors",
                    question=(
                        "How many floors do you want to propose, "
                        "if you have a preference?"
                    ),
                    required=False,
                )
            )

        # Parking preference is user intent.
        if not self._first_value(
            facts,
            "parking_mode",
        ):
            missing.append(
                PlanningUserQuestion(
                    field="parking_mode",
                    question=(
                        "What is your parking preference?"
                    ),
                    required=False,
                    options=[
                        "Maximum practical parking",
                        "Minimum required parking",
                        "Balanced",
                    ],
                )
            )

        return PlanningRequirementResult(
            missing=missing,
            complete=not any(
                question.required
                for question in missing
            ),
        )

    @staticmethod
    def _first_value(
        facts: Any,
        field_name: str,
    ) -> Any:

        try:
            value = getattr(
                facts,
                field_name,
                None,
            )

            if value is not None:
                return value

            values = getattr(
                facts,
                "values",
                None,
            )

            if isinstance(values, dict):
                return values.get(
                    field_name
                )

        except Exception:
            pass

        return None

    @classmethod
    def _require(
        cls,
        facts: Any,
        missing: list[PlanningUserQuestion],
        field_name: str,
        question: str,
    ) -> None:

        if cls._first_value(
            facts,
            field_name,
        ):
            return

        missing.append(
            PlanningUserQuestion(
                field=field_name,
                question=question,
            )
        )
