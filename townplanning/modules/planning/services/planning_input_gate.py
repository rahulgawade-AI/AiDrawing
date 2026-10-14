from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from townplanning.modules.planning.domain.missing_planning_fact import (
    MissingPlanningFact,
)

from townplanning.modules.planning.services.udcpr_design_inputs import (
    ALL_UDCPR_DESIGN_INPUTS,
    UDCPRInputRequirement,
)


@dataclass(slots=True)
class PlanningInputGateResult:
    """
    Result of UDCPR-aware planning input validation.
    """

    ready: bool

    missing: list[MissingPlanningFact] = field(
        default_factory=list
    )

    available: dict[str, Any] = field(
        default_factory=dict
    )

    conditional: list[MissingPlanningFact] = field(
        default_factory=list
    )

    needs_confirmation: list[MissingPlanningFact] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:

        return {
            "ready": self.ready,

            "missing_information": [
                {
                    "field": item.field,
                    "question": item.question,
                    "reason": item.reason,
                    "required_for": item.required_for,
                }
                for item in self.missing
            ],

            "conditional_information": [
                {
                    "field": item.field,
                    "question": item.question,
                    "reason": item.reason,
                    "required_for": item.required_for,
                }
                for item in self.conditional
            ],

            "confirmation_required": [
                {
                    "field": item.field,
                    "question": item.question,
                    "reason": item.reason,
                    "required_for": item.required_for,
                }
                for item in self.needs_confirmation
            ],

            "available_information": dict(
                self.available
            ),
        }


class PlanningInputGate:
    """
    UDCPR-aware planning/design input gate.

    IMPORTANT
    ---------

    This class DOES NOT calculate:

        - FSI
        - setbacks
        - parking
        - height
        - fire requirements
        - building geometry

    It only determines whether enough information exists
    to safely evaluate those requirements.

    Actual regulatory values continue to come from:

        PostgreSQL / deterministic rule engine
        +
        UDCPR source evidence
    """

    # ==============================================================
    # INITIALIZATION
    # ==============================================================

    def __init__(
        self,
        requirements=ALL_UDCPR_DESIGN_INPUTS,
    ) -> None:

        self.requirements = tuple(
            requirements
        )

    # ==============================================================
    # PUBLIC API
    # ==============================================================

    def evaluate(
        self,
        facts: Any,
        applicable_rules: list[Any] | None = None,
    ) -> PlanningInputGateResult:

        available = self._facts_to_dict(
            facts
        )

        missing: list[
            MissingPlanningFact
        ] = []

        conditional: list[
            MissingPlanningFact
        ] = []

        needs_confirmation: list[
            MissingPlanningFact
        ] = []

        # ==========================================================
        # REQUIREMENT CHECK
        # ==========================================================

        for requirement in self.requirements:

            # ------------------------------------------------------
            # Conditional requirements
            # ------------------------------------------------------

            if not self._is_required(
                requirement,
                available,
            ):
                continue

            # ------------------------------------------------------
            # Already available
            # ------------------------------------------------------

            if self._has_fact(
                available,
                requirement.field,
            ):

                # --------------------------------------------------
                # Check extraction confidence.
                # --------------------------------------------------

                if not self._fact_confidence_sufficient(
                    facts,
                    requirement.field,
                ):

                    self._append_confirmation_once(
                        needs_confirmation,
                        MissingPlanningFact(
                            field=requirement.field,
                            question=(
                                f"Please confirm the value for "
                                f"{requirement.field}."
                            ),
                            reason=(
                                "The value was extracted or supplied "
                                "with insufficient confidence."
                            ),
                            required_for=list(
                                requirement.required_for
                            ),
                        ),
                    )

                continue

            # ------------------------------------------------------
            # Missing requirement
            # ------------------------------------------------------

            item = MissingPlanningFact(
                field=requirement.field,

                question=requirement.question,

                reason=requirement.reason,

                required_for=list(
                    requirement.required_for
                ),
            )

            # ------------------------------------------------------
            # Conditional vs core
            # ------------------------------------------------------

            if requirement.conditional_on:

                self._append_conditional_once(
                    conditional,
                    item,
                )

            else:

                self._append_missing_once(
                    missing,
                    item,
                )

        # ==========================================================
        # ADDITIONAL DERIVED REQUIREMENTS
        # ==========================================================

        self._check_derived_requirements(
            available=available,
            missing=missing,
            conditional=conditional,
        )

        # ==========================================================
        # READINESS
        # ==========================================================

        return PlanningInputGateResult(
            ready=not missing,
            missing=missing,
            available=available,
            conditional=conditional,
            needs_confirmation=needs_confirmation,
        )

    # ==============================================================
    # REQUIREMENT EVALUATION
    # ==============================================================

    def _is_required(
        self,
        requirement: UDCPRInputRequirement,
        available: dict[str, Any],
    ) -> bool:

        conditions = requirement.conditional_on

        # No conditions = always required.
        if not conditions:
            return True

        # Every conditional dependency must be active.
        for condition in conditions:

            value = available.get(
                condition
            )

            if not self._condition_active(
                value
            ):
                return False

        return True

    # ==============================================================
    # DERIVED REQUIREMENTS
    # ==============================================================

    def _check_derived_requirements(
        self,
        *,
        available: dict[str, Any],
        missing: list[MissingPlanningFact],
        conditional: list[MissingPlanningFact],
    ) -> None:

        # ==========================================================
        # ROAD WIDTH
        # ==========================================================

        road_width = available.get(
            "road_width"
        )

        road_widths = available.get(
            "road_widths"
        )

        has_road_width = (
            self._has_value(
                road_width
            )
            or self._has_value(
                road_widths
            )
        )

        if not has_road_width:

            self._append_missing_once(
                missing,
                MissingPlanningFact(
                    field="road_width",
                    question=(
                        "What is the width of each road "
                        "abutting the plot in metres?"
                    ),
                    reason=(
                        "Road width is used by UDCPR for "
                        "FSI, setbacks, margins and "
                        "building potential."
                    ),
                    required_for=[
                        "FSI",
                        "setbacks",
                        "margins",
                        "building potential",
                    ],
                ),
            )

        # ==========================================================
        # ROAD FRONTAGE
        # ==========================================================

        frontage_count = available.get(
            "road_frontage_count"
        )

        road_frontages = available.get(
            "road_frontages"
        )

        road_locations = available.get(
            "road_locations"
        )

        has_frontage = (
            self._has_value(
                frontage_count
            )
            or self._has_value(
                road_locations
            )
            or self._has_value(
                road_frontages
            )
        )

        if not has_frontage:

            self._append_missing_once(
                missing,
                MissingPlanningFact(
                    field="road_frontage",
                    question=(
                        "Which side or sides of the plot "
                        "abut a road?"
                    ),
                    reason=(
                        "Road frontage determines the "
                        "road-facing building sides and "
                        "front setback treatment."
                    ),
                    required_for=[
                        "front setback",
                        "site access",
                        "building orientation",
                    ],
                ),
            )

        # ==========================================================
        # MULTIPLE ROADS
        # ==========================================================

        if self._has_multiple_roads(
            available
        ):

            if not self._has_value(
                available.get(
                    "road_frontages"
                )
            ):

                self._append_conditional_once(
                    conditional,
                    MissingPlanningFact(
                        field="road_frontages",
                        question=(
                            "Provide each road frontage "
                            "with its side/location and "
                            "road width."
                        ),
                        reason=(
                            "A plot abutting multiple roads "
                            "must retain road-specific "
                            "information for building "
                            "placement and margins."
                        ),
                        required_for=[
                            "front setback",
                            "roadside margin",
                            "building orientation",
                        ],
                    ),
                )

        # ==========================================================
        # GROUP HOUSING
        # ==========================================================

        if self._condition_active(
            available.get(
                "group_housing"
            )
        ):

            if not self._has_value(
                available.get(
                    "number_of_buildings"
                )
            ):

                self._append_conditional_once(
                    conditional,
                    MissingPlanningFact(
                        field="number_of_buildings",
                        question=(
                            "How many buildings or wings "
                            "are proposed in the group "
                            "housing scheme?"
                        ),
                        reason=(
                            "Multiple-building layouts "
                            "require building-separation "
                            "and internal-access planning."
                        ),
                        required_for=[
                            "building separation",
                            "internal roads",
                            "layout planning",
                        ],
                    ),
                )

        # ==========================================================
        # MIXED USE
        # ==========================================================

        if self._condition_active(
            available.get(
                "mixed_use"
            )
        ):

            if not self._has_value(
                available.get(
                    "requested_commercial_area"
                )
            ):

                self._append_conditional_once(
                    conditional,
                    MissingPlanningFact(
                        field="requested_commercial_area",
                        question=(
                            "What commercial area is "
                            "proposed?"
                        ),
                        reason=(
                            "The commercial component "
                            "affects use-specific and "
                            "parking requirements."
                        ),
                        required_for=[
                            "mixed-use planning",
                            "parking",
                            "occupancy",
                        ],
                    ),
                )

        # ==========================================================
        # REDEVELOPMENT
        # ==========================================================

        redevelopment = (
            self._condition_active(
                available.get(
                    "redevelopment"
                )
            )
            or str(
                available.get(
                    "development_type",
                    "",
                )
            ).strip().lower()
            in {
                "redevelopment",
                "reconstruction",
            }
        )

        if redevelopment:

            if not self._condition_active(
                available.get(
                    "existing_building"
                )
            ):

                self._append_conditional_once(
                    conditional,
                    MissingPlanningFact(
                        field="existing_building",
                        question=(
                            "Is there an existing authorised "
                            "building on the plot?"
                        ),
                        reason=(
                            "Redevelopment provisions depend "
                            "on the existing authorised "
                            "building."
                        ),
                        required_for=[
                            "redevelopment FSI",
                            "existing parking",
                        ],
                    ),
                )

        # ==========================================================
        # AIRPORT
        # ==========================================================

        if self._condition_active(
            available.get(
                "airport_restriction"
            )
        ):

            if not self._has_value(
                available.get(
                    "site_elevation"
                )
            ):

                self._append_conditional_once(
                    conditional,
                    MissingPlanningFact(
                        field="site_elevation",
                        question=(
                            "What is the site elevation "
                            "above mean sea level?"
                        ),
                        reason=(
                            "UDCPR uses site elevation when "
                            "converting airport CCZM elevation "
                            "to allowable building height."
                        ),
                        required_for=[
                            "airport-controlled height",
                        ],
                    ),
                )

            if not self._has_value(
                available.get(
                    "cczm_permissible_elevation"
                )
            ):

                self._append_conditional_once(
                    conditional,
                    MissingPlanningFact(
                        field="cczm_permissible_elevation",
                        question=(
                            "What maximum top elevation is "
                            "permitted by the applicable "
                            "Airport Authority CCZM?"
                        ),
                        reason=(
                            "The airport restriction must be "
                            "known before finalising building "
                            "height."
                        ),
                        required_for=[
                            "maximum building height",
                        ],
                    ),
                )

        # ==========================================================
        # PARKING
        # ==========================================================

        building_use = str(
            available.get(
                "building_use",
                "",
            )
        ).strip().lower()

        if (
            "residential" in building_use
            or self._condition_active(
                available.get(
                    "group_housing"
                )
            )
        ):

            # ------------------------------------------------------
            # Unit count is a design output unless the user has
            # explicitly specified a mandatory count.
            # ------------------------------------------------------

            if not self._has_value(
                available.get(
                    "tenement_carpet_areas"
                )
            ):

                self._append_conditional_once(
                    conditional,
                    MissingPlanningFact(
                        field="tenement_carpet_areas",
                        question=(
                            "What is the carpet area of "
                            "each residential tenement or "
                            "each tenement-size category?"
                        ),
                        reason=(
                            "Table 8-B classifies residential "
                            "parking by tenement carpet area."
                        ),
                        required_for=[
                            "car parking",
                            "two-wheeler parking",
                            "visitor parking",
                        ],
                    ),
                )

        # ==========================================================
        # BUILDING HEIGHT / FLOORS
        # ==========================================================

        requested_height = available.get(
            "requested_height"
        )

        requested_floors = available.get(
            "requested_floors"
        )

        floor_height = available.get(
            "floor_height"
        )

        building_height = available.get(
            "building_height"
        )

        # ----------------------------------------------------------
        # CASE 1:
        # Explicit proposed height exists.
        # ----------------------------------------------------------

        if (
            self._has_value(
                requested_height
            )
            or self._has_value(
                building_height
            )
        ):
            pass

        # ----------------------------------------------------------
        # CASE 2:
        # Floors + floor height exist.
        #
        # The actual height derivation belongs downstream.
        # ----------------------------------------------------------

        elif (
            self._has_value(
                requested_floors
            )
            and self._has_value(
                floor_height
            )
        ):
            pass

        # ----------------------------------------------------------
        # CASE 3:
        # Floors supplied, floor height missing.
        # ----------------------------------------------------------

        elif self._has_value(
            requested_floors
        ):

            self._append_missing_once(
                missing,
                MissingPlanningFact(
                    field="floor_height",
                    question=(
                        "What floor-to-floor height is proposed "
                        "for the building, in metres?"
                    ),
                    reason=(
                        "The proposed building height must be "
                        "established before finalising "
                        "height-dependent planning and "
                        "life-safety requirements."
                    ),
                    required_for=[
                        "building height",
                        "height-dependent UDCPR provisions",
                        "fire/life-safety evaluation",
                        "staircase requirements",
                        "lift requirements",
                    ],
                ),
            )

        # ----------------------------------------------------------
        # CASE 4:
        # Neither height nor floors supplied.
        #
        # Do not force a user value.
        #
        # The regulatory engine can subsequently establish the
        # permissible envelope from applicable rules.
        # ----------------------------------------------------------

        else:
            pass

    # ==============================================================
    # FACT CONVERSION
    # ==============================================================

    @staticmethod
    def _facts_to_dict(
        facts: Any,
    ) -> dict[str, Any]:

        if facts is None:
            return {}

        # ----------------------------------------------------------
        # Dictionary input
        # ----------------------------------------------------------

        if isinstance(
            facts,
            dict,
        ):
            result = dict(
                facts
            )

        else:

            # ------------------------------------------------------
            # Prefer PlanningFacts.to_dict()
            # ------------------------------------------------------

            to_dict = getattr(
                facts,
                "to_dict",
                None,
            )

            if callable(
                to_dict
            ):

                value = to_dict()

                if isinstance(
                    value,
                    dict,
                ):
                    result = dict(
                        value
                    )

                else:
                    result = {}

            else:

                result = {}

                dataclass_fields = getattr(
                    facts,
                    "__dataclass_fields__",
                    {},
                )

                for name in dataclass_fields:

                    try:

                        value = getattr(
                            facts,
                            name,
                        )

                    except Exception:

                        continue

                    if value is not None:

                        result[name] = value

            # ------------------------------------------------------
            # Overlay PlanningFacts.values
            # ------------------------------------------------------

            values = getattr(
                facts,
                "values",
                None,
            )

            if isinstance(
                values,
                dict,
            ):

                result.update(
                    values
                )

        # ==========================================================
        # CANONICAL COMPATIBILITY ALIASES
        # ==========================================================

        # ----------------------------------------------------------
        # PlanningFacts uses:
        #
        #     boundary
        #
        # Older design-input definitions may use:
        #
        #     plot_boundary
        #
        # Do NOT add plot_boundary to PlanningFacts.
        # This alias exists only inside the gate's evaluation view.
        # ----------------------------------------------------------

        if (
            "boundary" in result
            and "plot_boundary" not in result
            and result["boundary"] is not None
        ):

            result[
                "plot_boundary"
            ] = result[
                "boundary"
            ]

        # ----------------------------------------------------------
        # Road frontage compatibility
        # ----------------------------------------------------------

        if (
            "road_frontages" in result
            and "road_frontage" not in result
            and result["road_frontages"]
        ):

            result[
                "road_frontage"
            ] = result[
                "road_frontages"
            ]

        # ----------------------------------------------------------
        # Singular road width compatibility
        # ----------------------------------------------------------

        if (
            "road_widths" in result
            and "road_width" not in result
            and isinstance(
                result["road_widths"],
                (list, tuple),
            )
            and len(
                result["road_widths"]
            ) == 1
        ):

            result[
                "road_width"
            ] = result[
                "road_widths"
            ][0]

        return result

    # ==============================================================
    # CONFIDENCE
    # ==============================================================

    @staticmethod
    def _fact_confidence_sufficient(
        facts: Any,
        field: str,
        threshold: float = 0.85,
    ) -> bool:

        confidence = getattr(
            facts,
            "fact_confidence",
            None,
        )

        if not isinstance(
            confidence,
            dict,
        ):
            return True

        value = confidence.get(
            field
        )

        if value is None:
            return True

        try:

            return (
                float(value)
                >= threshold
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

    # ==============================================================
    # VALUE HELPERS
    # ==============================================================

    @staticmethod
    def _has_value(
        value: Any,
    ) -> bool:

        if value is None:
            return False

        if isinstance(
            value,
            str,
        ):

            return bool(
                value.strip()
            )

        if isinstance(
            value,
            (list, tuple, set, dict),
        ):

            return len(
                value
            ) > 0

        return True

    @classmethod
    def _has_fact(
        cls,
        values: dict[str, Any],
        field: str,
    ) -> bool:

        return cls._has_value(
            values.get(field)
        )

    @classmethod
    def _condition_active(
        cls,
        value: Any,
    ) -> bool:

        if value is None:
            return False

        if isinstance(
            value,
            bool,
        ):

            return value

        if isinstance(
            value,
            str,
        ):

            normalized = (
                value
                .strip()
                .lower()
            )

            if normalized in {
                "",
                "false",
                "no",
                "none",
                "null",
                "unknown",
                "not applicable",
                "n/a",
            }:

                return False

            if normalized in {
                "true",
                "yes",
            }:

                return True

            return True

        return bool(
            value
        )

    # ==============================================================
    # MULTIPLE ROADS
    # ==============================================================

    @staticmethod
    def _has_multiple_roads(
        available: dict[str, Any],
    ) -> bool:

        frontage_count = available.get(
            "road_frontage_count"
        )

        if (
            isinstance(
                frontage_count,
                int,
            )
            and frontage_count > 1
        ):

            return True

        road_widths = available.get(
            "road_widths"
        )

        if (
            isinstance(
                road_widths,
                (list, tuple),
            )
            and len(
                road_widths
            ) > 1
        ):

            return True

        road_frontages = available.get(
            "road_frontages"
        )

        if (
            isinstance(
                road_frontages,
                (list, tuple),
            )
            and len(
                road_frontages
            ) > 1
        ):

            return True

        road_locations = available.get(
            "road_locations"
        )

        if (
            isinstance(
                road_locations,
                (list, tuple),
            )
            and len(
                road_locations
            ) > 1
        ):

            return True

        return False

    # ==============================================================
    # LIST HELPERS
    # ==============================================================

    @staticmethod
    def _append_missing_once(
        items: list[
            MissingPlanningFact
        ],
        item: MissingPlanningFact,
    ) -> None:

        if any(
            existing.field
            == item.field
            for existing in items
        ):

            return

        items.append(
            item
        )

    @staticmethod
    def _append_conditional_once(
        items: list[
            MissingPlanningFact
        ],
        item: MissingPlanningFact,
    ) -> None:

        if any(
            existing.field
            == item.field
            for existing in items
        ):

            return

        items.append(
            item
        )

    @staticmethod
    def _append_confirmation_once(
        items: list[
            MissingPlanningFact
        ],
        item: MissingPlanningFact,
    ) -> None:

        if any(
            existing.field
            == item.field
            for existing in items
        ):

            return

        items.append(
            item
        )