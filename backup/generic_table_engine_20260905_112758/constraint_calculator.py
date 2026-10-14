from __future__ import annotations

import re
from typing import Any

from townplanning.modules.planning.domain.applicable_rule import (
    ApplicableRule,
)
from townplanning.modules.planning.domain.planning_constraints import (
    PlanningConstraints,
)
from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.planning.regulations.table_parking_calculator import (
    TableParkingCalculator,
)


class ConstraintCalculator:
    """
    Converts applicable UDCPR rules into PlanningConstraints.

    Responsibilities
    -----------------
    1. Apply directly stated numeric UDCPR constraints.
    2. Preserve formula/reference based rules in metadata.
    3. Calculate deterministic derived values.
    4. Apply persisted Table No.8-B parking requirements.
    5. Never invent a regulatory value when the database does not
       provide enough information.
    """

    def __init__(self, table_repository=None):
        self.table_repository = table_repository
        self.table_parking_calculator = TableParkingCalculator()

    # ============================================================
    # MAIN CALCULATION
    # ============================================================

    def calculate(
        self,
        facts: PlanningFacts,
        rules: list[ApplicableRule],
    ) -> PlanningConstraints:

        constraints = PlanningConstraints()

        applicable = [
            rule
            for rule in rules
            if getattr(rule, "status", None)
            in {"applicable", "unconditional"}
        ]

        unresolved = [
            rule
            for rule in rules
            if getattr(rule, "status", None) == "unresolved"
        ]

        rejected = [
            rule
            for rule in rules
            if getattr(rule, "status", None)
            in {"not_applicable", "invalid"}
        ]

        constraints.applied_rules = applicable
        constraints.unresolved_rules = unresolved
        constraints.rejected_rules = rejected

        # --------------------------------------------------------
        # Regulatory traceability
        # --------------------------------------------------------

        constraints.metadata["regulatory_requirements"] = []

        self._extract_regulatory_requirements(
            constraints,
            applicable,
        )

        # --------------------------------------------------------
        # Apply rules
        # --------------------------------------------------------

        for rule in applicable:
            self._apply_rule(
                constraints=constraints,
                rule=rule,
            )

        # --------------------------------------------------------
        # Table-driven parking
        # --------------------------------------------------------

        self._apply_table_parking(
            facts=facts,
            constraints=constraints,
        )

        # --------------------------------------------------------
        # Derived calculations
        # --------------------------------------------------------

        self._calculate_fsi(
            facts=facts,
            constraints=constraints,
        )

        self._calculate_built_up_area(
            facts=facts,
            constraints=constraints,
        )

        self._calculate_height(
            facts=facts,
            constraints=constraints,
        )

        # --------------------------------------------------------
        # Audit information
        # --------------------------------------------------------

        constraints.metadata.update(
            {
                "plot_area": facts.plot_area,
                "road_width": facts.road_width,
                "building_type": facts.building_type,
                "building_use": facts.building_use,
                "rule_count": len(rules),
                "applicable_rule_count": len(applicable),
                "unresolved_rule_count": len(unresolved),
            }
        )

        return constraints

    # ============================================================
    # RULE APPLICATION
    # ============================================================

    def _apply_rule(
        self,
        constraints: PlanningConstraints,
        rule: ApplicableRule,
    ) -> None:

        category = (
            getattr(rule, "category", "") or ""
        ).strip().lower()

        name = (
            getattr(rule, "name", "") or ""
        ).strip().lower()

        result = getattr(rule, "result", None)

        if not isinstance(result, dict):
            result = {}

        # --------------------------------------------------------
        # Land use
        # --------------------------------------------------------

        self._apply_land_use(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------------
        # FSI
        # --------------------------------------------------------

        self._apply_fsi(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------------
        # TDR
        # --------------------------------------------------------

        if (
            "tdr" in category
            or "tdr" in name
            or "transferable" in name
        ):
            self._apply_tdr_fsi(
                constraints=constraints,
                result=result,
            )

        # --------------------------------------------------------
        # Incentive FSI
        # --------------------------------------------------------

        if (
            "incentive" in category
            or "incentive" in name
            or "additional fsi" in name
        ):
            self._apply_incentive_fsi(
                constraints=constraints,
                result=result,
            )

        # --------------------------------------------------------
        # Ground coverage
        # --------------------------------------------------------

        if (
            "coverage" in category
            or "coverage" in name
            or "ground" in category
        ):
            self._apply_ground_coverage(
                constraints=constraints,
                result=result,
            )

        # --------------------------------------------------------
        # Setbacks
        # --------------------------------------------------------

        if (
            "setback" in category
            or "setback" in name
            or "margin" in category
            or "margin" in name
        ):
            self._apply_setbacks(
                constraints=constraints,
                result=result,
            )

        # --------------------------------------------------------
        # Height / storeys
        # --------------------------------------------------------

        if (
            "height" in category
            or "height" in name
            or "storey" in category
            or "storey" in name
            or "floor" in name
        ):
            self._apply_height_and_storeys(
                constraints=constraints,
                result=result,
            )

        # --------------------------------------------------------
        # Parking
        # --------------------------------------------------------

        if (
            "parking" in category
            or "parking" in name
        ):
            self._apply_parking(
                constraints,
                category,
                name,
                result,
            )

            self._apply_parking_area(
                constraints=constraints,
                result=result,
            )

        # --------------------------------------------------------
        # Fire
        # --------------------------------------------------------

        self._apply_fire(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------------
        # Circulation
        # --------------------------------------------------------

        self._apply_circulation(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------------
        # Accessibility
        # --------------------------------------------------------

        self._apply_accessibility(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------------
        # Open spaces
        # --------------------------------------------------------

        self._apply_open_spaces(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------------
        # Special conditions
        # --------------------------------------------------------

        self._apply_special_conditions(
            constraints,
            category,
            name,
            result,
        )

    # ============================================================
    # LAND USE
    # ============================================================

    def _apply_land_use(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        permitted = self._list_value(
            result,
            "permitted_uses",
            "uses",
            "permittedUses",
        )

        if permitted:
            for use in permitted:
                use = str(use)

                if use not in constraints.permitted_uses:
                    constraints.permitted_uses.append(use)

        if (
            "mixed use" in category
            or "mixed use" in name
        ):
            value = self._bool_value(
                result,
                "allowed",
                "permitted",
                "mixed_use_allowed",
                "mixedUseAllowed",
            )

            if value is not None:
                constraints.mixed_use_allowed = value

    # ============================================================
    # FSI
    # ============================================================

    def _apply_fsi(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        basic = self._number_value(
            result,
            "basic_fsi",
            "basicFSI",
            "fsi",
            "permissible_fsi",
            "permissibleFSI",
        )

        premium = self._number_value(
            result,
            "premium_fsi",
            "premiumFSI",
            "additional_fsi",
            "additionalFSI",
            "premium",
        )

        tdr = self._number_value(
            result,
            "tdr_fsi",
            "tdrFSI",
            "tdr",
        )

        incentive = self._number_value(
            result,
            "incentive_fsi",
            "incentiveFSI",
            "incentive",
        )

        maximum = self._number_value(
            result,
            "maximum_fsi",
            "maximumFSI",
            "max_fsi",
            "maxFSI",
            "maximum_building_potential",
            "maximumBuildingPotential",
            "maximum_potential",
            "maximumPotential",
            "maximum_permissible_fsi",
            "maximumPermissibleFSI",
            "maximum_total_fsi",
            "maximumTotalFSI",
            "max_total_fsi",
        )

        total = self._number_value(
            result,
            "total_fsi",
            "totalFSI",
        )

        if basic is not None:
            constraints.basic_fsi = self._max_or_set(
                constraints.basic_fsi,
                basic,
            )

        if premium is not None:
            constraints.premium_fsi = self._max_or_set(
                constraints.premium_fsi,
                premium,
            )

        if tdr is not None:
            constraints.tdr_fsi = self._max_or_set(
                constraints.tdr_fsi,
                tdr,
            )

        if incentive is not None:
            constraints.incentive_fsi = self._max_or_set(
                constraints.incentive_fsi,
                incentive,
            )

        if maximum is not None:
            constraints.maximum_fsi = self._min_or_set(
                constraints.maximum_fsi,
                maximum,
            )

        if total is not None:
            constraints.total_fsi = self._min_or_set(
                constraints.total_fsi,
                total,
            )

        # --------------------------------------------------------
        # Premium FSI from explicit "difference" rule
        # --------------------------------------------------------

        action = str(
            result.get("action", "")
        ).strip().lower()

        if (
            "premium" in name
            and (
                action == "pay_premium"
                or action == "calculate premium"
            )
            and constraints.maximum_fsi is not None
        ):

            base_fsi = sum(
                value
                for value in (
                    constraints.basic_fsi,
                    constraints.tdr_fsi,
                    constraints.incentive_fsi,
                )
                if value is not None
            )

            available = max(
                0.0,
                constraints.maximum_fsi - base_fsi,
            )

            if available > 0:
                constraints.premium_fsi = (
                    self._max_or_set(
                        constraints.premium_fsi,
                        available,
                    )
                )

    # ============================================================
    # TDR FSI
    # ============================================================

    def _apply_tdr_fsi(
        self,
        constraints: PlanningConstraints,
        result: dict[str, Any],
    ) -> None:

        value = self._first_number(
            result,
            "tdr_fsi",
            "tdrFSI",
            "tdr",
            "tdr_fsi_allowed",
            "tdr_fsi_permissible",
            "transferable_development_rights_fsi",
            "transferableDevelopmentRightsFSI",
        )

        if value is not None:
            constraints.tdr_fsi = self._max_or_set(
                constraints.tdr_fsi,
                value,
            )

    # ============================================================
    # INCENTIVE FSI
    # ============================================================

    def _apply_incentive_fsi(
        self,
        constraints: PlanningConstraints,
        result: dict[str, Any],
    ) -> None:

        value = self._first_number(
            result,
            "incentive_fsi",
            "incentiveFSI",
            "incentive",
            "incentive_fsi_allowed",
            "incentive_fsi_permissible",
            "additional_fsi",
            "additionalFSI",
        )

        if value is not None:
            constraints.incentive_fsi = self._max_or_set(
                constraints.incentive_fsi,
                value,
            )

    # ============================================================
    # GROUND COVERAGE
    # ============================================================

    def _apply_ground_coverage(
        self,
        constraints: PlanningConstraints,
        result: dict[str, Any],
    ) -> None:

        value = self._first_number(
            result,
            "maximum_ground_coverage",
            "maximumGroundCoverage",
            "ground_coverage",
            "groundCoverage",
            "ground_coverage_percent",
            "groundCoveragePercent",
            "maximum_coverage",
            "maximumCoverage",
            "coverage",
            "coverage_percent",
        )

        if value is not None:
            constraints.maximum_ground_coverage = (
                self._min_or_set(
                    constraints.maximum_ground_coverage,
                    value,
                )
            )

    # ============================================================
    # SETBACKS
    # ============================================================

    def _apply_setbacks(
        self,
        constraints: PlanningConstraints,
        result: dict[str, Any],
    ) -> None:

        front = self._first_number(
            result,
            "front_setback",
            "frontSetback",
            "front_margin",
            "frontMargin",
            "minimum_front_setback",
            "minimumFrontSetback",
            "front_margin_required",
            "frontMarginRequired",
        )

        rear = self._first_number(
            result,
            "rear_setback",
            "rearSetback",
            "rear_margin",
            "rearMargin",
            "minimum_rear_setback",
            "minimumRearSetback",
            "rear_margin_required",
            "rearMarginRequired",
        )

        left = self._first_number(
            result,
            "side_setback_left",
            "sideSetbackLeft",
            "left_setback",
            "leftSetback",
            "left_margin",
            "leftMargin",
            "minimum_left_setback",
            "minimumLeftSetback",
        )

        right = self._first_number(
            result,
            "side_setback_right",
            "sideSetbackRight",
            "right_setback",
            "rightSetback",
            "right_margin",
            "rightMargin",
            "minimum_right_setback",
            "minimumRightSetback",
        )

        if front is not None:
            constraints.front_setback = self._max_or_set(
                constraints.front_setback,
                front,
            )

        if rear is not None:
            constraints.rear_setback = self._max_or_set(
                constraints.rear_setback,
                rear,
            )

        if left is not None:
            constraints.side_setback_left = self._max_or_set(
                constraints.side_setback_left,
                left,
            )

        if right is not None:
            constraints.side_setback_right = self._max_or_set(
                constraints.side_setback_right,
                right,
            )

    # ============================================================
    # HEIGHT / STOREYS
    # ============================================================

    def _apply_height_and_storeys(
        self,
        constraints: PlanningConstraints,
        result: dict[str, Any],
    ) -> None:

        height = self._first_number(
            result,
            "maximum_height_m",
            "maximumHeightM",
            "maximum_height",
            "maximumHeight",
            "height_m",
            "heightM",
            "height",
            "permissible_height",
            "maximum_building_height",
            "maximumBuildingHeight",
        )

        storeys = self._first_number(
            result,
            "maximum_storeys",
            "maximumStoreys",
            "maximum_floors",
            "maximumFloors",
            "storeys",
            "floors",
            "permissible_storeys",
            "permissible_floors",
        )

        if height is not None:
            constraints.maximum_height_m = (
                self._min_or_set(
                    constraints.maximum_height_m,
                    height,
                )
            )

        if storeys is not None:
            constraints.maximum_storeys = (
                self._min_int_or_set(
                    constraints.maximum_storeys,
                    int(storeys),
                )
            )

    # ============================================================
    # PARKING
    # ============================================================

    def _apply_parking(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        car = self._number_value(
            result,
            "car_parking_required",
            "carParkingRequired",
            "car_parking",
            "cars",
        )

        two_wheeler = self._number_value(
            result,
            "two_wheeler_parking_required",
            "twoWheelerParkingRequired",
            "two_wheeler_parking",
            "motorcycle_parking",
        )

        visitor = self._number_value(
            result,
            "visitor_parking_required",
            "visitorParkingRequired",
            "visitor_parking",
        )

        area = self._number_value(
            result,
            "parking_area_required",
            "parkingAreaRequired",
            "parking_area",
        )

        quantity = self._number_value(
            result,
            "quantity",
            "count",
        )

        resource = str(
            result.get("resource", "")
        ).strip().lower()

        action = str(
            result.get("action", "")
        ).strip().lower()

        if (
            quantity is not None
            and action in {
                "provide",
                "require",
                "calculate",
            }
        ):
            if (
                "two-wheeler" in resource
                or "two wheeler" in resource
                or "motorcycle" in resource
            ):
                two_wheeler = quantity

            elif (
                "car" in resource
                or "vehicle" in resource
            ):
                car = quantity

        if car is not None:
            constraints.car_parking_required = (
                self._max_or_set(
                    constraints.car_parking_required,
                    car,
                )
            )

        if two_wheeler is not None:
            constraints.two_wheeler_parking_required = (
                self._max_or_set(
                    constraints.two_wheeler_parking_required,
                    two_wheeler,
                )
            )

        if visitor is not None:
            constraints.visitor_parking_required = (
                self._max_or_set(
                    constraints.visitor_parking_required,
                    visitor,
                )
            )

        if area is not None:
            constraints.parking_area_required = (
                self._max_or_set(
                    constraints.parking_area_required,
                    area,
                )
            )

    # ============================================================
    # TABLE 8-B PARKING
    # ============================================================

    def _apply_table_parking(
        self,
        facts: PlanningFacts,
        constraints: PlanningConstraints,
    ) -> None:

        # Existing calculator remains usable without database access.
        if self.table_repository is None:
            constraints.metadata["parking_table_result"] = {
                "status": "repository_not_configured",
                "table": "Table No.8-B",
            }
            return

        try:

            table = None

            # First try the authoritative persisted page.
            try:
                tables = self.table_repository.list_by_page(165)
            except Exception:
                tables = []

            for candidate in tables:

                title = str(
                    getattr(candidate, "title", "") or ""
                )

                headers = getattr(
                    candidate,
                    "headers",
                    [],
                ) or []

                header_text = " ".join(
                    str(value)
                    for value in headers
                )

                searchable = (
                    f"{title} {header_text}"
                ).lower()

                if (
                    "table no.8-b" in searchable
                    or "table no. 8-b" in searchable
                    or "parking requirements" in searchable
                ):
                    table = candidate
                    break

            # Fallback: search all persisted tables.
            if table is None:

                for candidate in self.table_repository.list():

                    title = str(
                        getattr(candidate, "title", "") or ""
                    )

                    headers = getattr(
                        candidate,
                        "headers",
                        [],
                    ) or []

                    header_text = " ".join(
                        str(value)
                        for value in headers
                    )

                    searchable = (
                        f"{title} {header_text}"
                    ).lower()

                    if (
                        "table no.8-b" in searchable
                        or "table no. 8-b" in searchable
                        or "parking requirements" in searchable
                    ):
                        table = candidate
                        break

            if table is None:

                constraints.metadata[
                    "parking_table_result"
                ] = {
                    "status": "table_not_found",
                    "table": "Table No.8-B",
                    "page": 165,
                }

                return

            result = (
                self.table_parking_calculator.calculate(
                    table,
                    facts,
                )
            )

            if not isinstance(result, dict):
                result = {
                    "status": "invalid_result",
                }

            constraints.metadata[
                "parking_table_result"
            ] = result

            source = result.get("source") or {}

            constraints.metadata[
                "parking_table_source"
            ] = {
                "table": source.get(
                    "table",
                    "Table No.8-B",
                ),
                "page": source.get(
                    "page",
                    getattr(table, "page", 165),
                ),
                "table_index": source.get(
                    "table_index",
                    getattr(table, "index", 1),
                ),
                "table_id": source.get(
                    "table_id",
                    getattr(table, "id", None),
                ),
            }

            if result.get("status") != "calculated":
                return

            car = result.get(
                "car_parking_required"
            )

            two_wheeler = result.get(
                "two_wheeler_parking_required"
            )

            visitor = result.get(
                "visitor_parking_required"
            )

            if car is not None:
                constraints.car_parking_required = car

            if two_wheeler is not None:
                constraints.two_wheeler_parking_required = (
                    two_wheeler
                )

            if visitor is not None:
                constraints.visitor_parking_required = visitor

        except Exception as exc:

            constraints.metadata[
                "parking_table_result"
            ] = {
                "status": "error",
                "table": "Table No.8-B",
                "page": 165,
                "error": str(exc),
            }

    # ============================================================
    # PARKING AREA
    # ============================================================

    def _apply_parking_area(
        self,
        constraints: PlanningConstraints,
        result: dict[str, Any],
    ) -> None:

        area = self._first_number(
            result,
            "parking_area_required",
            "parkingAreaRequired",
            "parking_area",
            "parkingArea",
            "minimum_parking_area",
            "minimumParkingArea",
            "parking_area_sq_m",
            "parkingAreaSqM",
        )

        if area is not None:
            constraints.parking_area_required = (
                self._max_or_set(
                    constraints.parking_area_required,
                    area,
                )
            )

    # ============================================================
    # FIRE
    # ============================================================

    def _apply_fire(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        fire_access = self._bool_value(
            result,
            "fire_access_required",
            "fireAccessRequired",
            "fire_access",
        )

        fire_lift = self._bool_value(
            result,
            "fire_lift_required",
            "fireLiftRequired",
            "fire_lift",
        )

        fire_stair = self._bool_value(
            result,
            "fire_staircase_required",
            "fireStaircaseRequired",
            "fire_staircase",
            "enclosed_staircase_required",
        )

        exits = self._integer_value(
            result,
            "minimum_exit_count",
            "minimumExitCount",
            "exit_count",
            "number_of_exits",
        )

        exit_width = self._number_value(
            result,
            "minimum_exit_width_m",
            "minimumExitWidth",
            "exit_width",
        )

        action = str(
            result.get("action", "")
        ).strip().lower()

        component = str(
            result.get("component", "")
        ).strip().lower()

        if action in {
            "require_fire_lift",
            "provide_fire_lift",
            "require fire lift",
        }:
            fire_lift = True

        if (
            action in {
                "require_fire_staircase",
                "require staircase",
            }
            or "fire escape staircase" in component
        ):
            fire_stair = True

        if fire_access is not None:
            constraints.fire_access_required = self._or_bool(
                constraints.fire_access_required,
                fire_access,
            )

        if fire_lift is not None:
            constraints.fire_lift_required = self._or_bool(
                constraints.fire_lift_required,
                fire_lift,
            )

        if fire_stair is not None:
            constraints.fire_staircase_required = self._or_bool(
                constraints.fire_staircase_required,
                fire_stair,
            )

        if exits is not None:
            constraints.minimum_exit_count = (
                self._max_int_or_set(
                    constraints.minimum_exit_count,
                    exits,
                )
            )

        if exit_width is not None:
            constraints.minimum_exit_width_m = (
                self._max_or_set(
                    constraints.minimum_exit_width_m,
                    exit_width,
                )
            )

    # ============================================================
    # CIRCULATION
    # ============================================================

    def _apply_circulation(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        stairs = self._integer_value(
            result,
            "staircase_count",
            "stair_count",
            "number_of_staircases",
        )

        stair_width = self._number_value(
            result,
            "staircase_width_m",
            "stair_width",
            "minimum_stair_width",
        )

        corridor = self._number_value(
            result,
            "corridor_width_m",
            "corridor_width",
            "minimum_corridor_width",
        )

        lift = self._bool_value(
            result,
            "lift_required",
            "liftRequired",
            "lift",
        )

        lift_count = self._integer_value(
            result,
            "lift_count",
            "number_of_lifts",
        )

        quantity = self._integer_value(
            result,
            "quantity",
            "count",
        )

        action = str(
            result.get("action", "")
        ).strip().lower()

        component = str(
            result.get("component", "")
        ).strip().lower()

        if (
            quantity is not None
            and (
                "stair" in component
                or "staircase" in component
            )
            and action in {"require", "provide"}
        ):
            stairs = quantity

        if stairs is not None:
            constraints.staircase_count = (
                self._max_int_or_set(
                    constraints.staircase_count,
                    stairs,
                )
            )

        if stair_width is not None:
            constraints.staircase_width_m = (
                self._max_or_set(
                    constraints.staircase_width_m,
                    stair_width,
                )
            )

        if corridor is not None:
            constraints.corridor_width_m = (
                self._max_or_set(
                    constraints.corridor_width_m,
                    corridor,
                )
            )

        if lift is not None:
            constraints.lift_required = self._or_bool(
                constraints.lift_required,
                lift,
            )

        if lift_count is not None:
            constraints.lift_count = (
                self._max_int_or_set(
                    constraints.lift_count,
                    lift_count,
                )
            )

    # ============================================================
    # ACCESSIBILITY
    # ============================================================

    def _apply_accessibility(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        entrance = self._bool_value(
            result,
            "accessible_entrance_required",
            "accessibleEntranceRequired",
            "accessible_entrance",
        )

        ramp = self._bool_value(
            result,
            "ramp_required",
            "rampRequired",
            "ramp",
        )

        ramp_width = self._number_value(
            result,
            "ramp_width_m",
            "ramp_width",
            "minimum_ramp_width",
        )

        gradient = self._number_value(
            result,
            "ramp_gradient",
            "gradient",
            "maximum_gradient",
        )

        if entrance is not None:
            constraints.accessible_entrance_required = (
                self._or_bool(
                    constraints.accessible_entrance_required,
                    entrance,
                )
            )

        if ramp is not None:
            constraints.ramp_required = (
                self._or_bool(
                    constraints.ramp_required,
                    ramp,
                )
            )

        if ramp_width is not None:
            constraints.ramp_width_m = (
                self._max_or_set(
                    constraints.ramp_width_m,
                    ramp_width,
                )
            )

        if gradient is not None:
            constraints.ramp_gradient = (
                self._min_or_set(
                    constraints.ramp_gradient,
                    gradient,
                )
            )

    # ============================================================
    # OPEN SPACE
    # ============================================================

    def _apply_open_spaces(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        recreational = self._number_value(
            result,
            "recreational_open_space_m2",
            "recreational_open_space",
            "recreation_space",
        )

        amenity = self._number_value(
            result,
            "amenity_space_m2",
            "amenity_space",
        )

        if recreational is not None:
            constraints.recreational_open_space_m2 = (
                self._max_or_set(
                    constraints.recreational_open_space_m2,
                    recreational,
                )
            )

        if amenity is not None:
            constraints.amenity_space_m2 = (
                self._max_or_set(
                    constraints.amenity_space_m2,
                    amenity,
                )
            )

    # ============================================================
    # SPECIAL CONDITIONS
    # ============================================================

    def _apply_special_conditions(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        road_widening = self._bool_value(
            result,
            "road_widening",
            "roadWidening",
            "road_widening_required",
        )

        reservation = self._bool_value(
            result,
            "reservation_present",
            "reservationPresent",
            "reservation",
        )

        special_height = self._number_value(
            result,
            "special_height_limit_m",
            "special_height_limit",
            "height_limit",
        )

        if road_widening is not None:
            constraints.road_widening = self._or_bool(
                constraints.road_widening,
                road_widening,
            )

        if reservation is not None:
            constraints.reservation_present = self._or_bool(
                constraints.reservation_present,
                reservation,
            )

        if special_height is not None:
            constraints.special_height_limit_m = (
                self._min_or_set(
                    constraints.special_height_limit_m,
                    special_height,
                )
            )

    # ============================================================
    # REGULATORY REQUIREMENTS / TRACEABILITY
    # ============================================================

    def _extract_regulatory_requirements(
        self,
        constraints: PlanningConstraints,
        rules: list[ApplicableRule],
    ) -> None:

        for rule in rules:

            if getattr(rule, "status", None) not in {
                "applicable",
                "unconditional",
            }:
                continue

            result = getattr(rule, "result", None)

            if not isinstance(result, dict):
                continue

            name = str(
                getattr(rule, "name", "")
            ).lower()

            category = str(
                getattr(rule, "category", "")
            ).lower()

            action = result.get("action")

            if (
                action
                or result.get("input_tables")
                or result.get("references")
                or result.get("formula")
                or result.get("calculation")
                or result.get("details")
            ):
                constraints.metadata[
                    "regulatory_requirements"
                ].append(
                    {
                        "rule_id": getattr(
                            rule,
                            "rule_id",
                            None,
                        ),
                        "name": getattr(
                            rule,
                            "name",
                            None,
                        ),
                        "category": getattr(
                            rule,
                            "category",
                            None,
                        ),
                        "action": action,
                        "result": result,
                    }
                )

            # ----------------------------------------------------
            # Stilt
            # ----------------------------------------------------

            stilt = result.get(
                "minimum_stilt_height"
            )

            if isinstance(stilt, dict):

                value = self._number_value(
                    stilt,
                    "value",
                    "amount",
                )

                if value is not None:
                    constraints.metadata[
                        "minimum_stilt_height_m"
                    ] = value

            # ----------------------------------------------------
            # Light / ventilation
            # ----------------------------------------------------

            opening = result.get(
                "opening_area"
            )

            if opening is not None:
                constraints.metadata[
                    "minimum_opening_area_requirement"
                ] = opening

            if (
                "opening" in result
                and "ventilation" in (
                    name + category
                )
            ):
                constraints.metadata[
                    "light_ventilation_requirement"
                ] = result

            # ----------------------------------------------------
            # Parking references
            # ----------------------------------------------------

            if (
                category == "parking"
                or "parking" in name
            ):

                if result.get("input_tables"):

                    constraints.metadata.setdefault(
                        "parking_rule_references",
                        [],
                    ).append(
                        {
                            "rule": getattr(
                                rule,
                                "name",
                                None,
                            ),
                            "tables": result[
                                "input_tables"
                            ],
                        }
                    )

                if result.get("action") in {
                    "calculate",
                    "provide_parking_spaces",
                    "require_off_street_parking",
                }:

                    constraints.metadata.setdefault(
                        "parking_requirements",
                        [],
                    ).append(
                        {
                            "rule": getattr(
                                rule,
                                "name",
                                None,
                            ),
                            "result": result,
                        }
                    )

            # ----------------------------------------------------
            # Life safety
            # ----------------------------------------------------

            if category in {
                "fire safety",
                "staircase",
                "egress",
                "exit requirements",
            }:

                constraints.metadata.setdefault(
                    "life_safety_requirements",
                    [],
                ).append(
                    {
                        "rule": getattr(
                            rule,
                            "name",
                            None,
                        ),
                        "category": getattr(
                            rule,
                            "category",
                            None,
                        ),
                        "result": result,
                    }
                )

    # ============================================================
    # DERIVED FSI
    # ============================================================

    def _calculate_fsi(
        self,
        facts: PlanningFacts,
        constraints: PlanningConstraints,
    ) -> None:

        components = [
            value
            for value in (
                constraints.basic_fsi,
                constraints.premium_fsi,
                constraints.tdr_fsi,
                constraints.incentive_fsi,
            )
            if value is not None
        ]

        if components:

            calculated_total = sum(
                components
            )

            if constraints.maximum_fsi is not None:
                calculated_total = min(
                    calculated_total,
                    constraints.maximum_fsi,
                )

            constraints.total_fsi = (
                calculated_total
            )

    # ============================================================
    # BUILT-UP AREA
    # ============================================================

    def _calculate_built_up_area(
        self,
        facts: PlanningFacts,
        constraints: PlanningConstraints,
    ) -> None:

        if facts.plot_area is None:
            return

        if constraints.total_fsi is None:
            return

        constraints.maximum_built_up_area = (
            facts.plot_area
            * constraints.total_fsi
        )

    # ============================================================
    # HEIGHT
    # ============================================================

    def _calculate_height(
        self,
        facts: PlanningFacts,
        constraints: PlanningConstraints,
    ) -> None:

        if (
            constraints.special_height_limit_m
            is not None
        ):

            constraints.maximum_height_m = (
                self._min_or_set(
                    constraints.maximum_height_m,
                    constraints.special_height_limit_m,
                )
            )

        if (
            constraints.maximum_storeys is not None
            and facts.floor_height is not None
        ):

            calculated_height = (
                constraints.maximum_storeys
                * facts.floor_height
            )

            constraints.maximum_height_m = (
                self._min_or_set(
                    constraints.maximum_height_m,
                    calculated_height,
                )
            )

    # ============================================================
    # VALUE EXTRACTION
    # ============================================================

    @staticmethod
    def _first_number(
        result: dict[str, Any],
        *keys: str,
    ) -> float | None:

        for key in keys:

            if key not in result:
                continue

            value = ConstraintCalculator._number_value(
                result,
                key,
            )

            if value is not None:
                return value

        return None

    @staticmethod
    def _number_value(
        result: dict[str, Any],
        *keys: str,
    ) -> float | None:

        def convert(value: Any) -> float | None:

            if value is None:
                return None

            if isinstance(value, bool):
                return None

            if isinstance(value, (int, float)):
                return float(value)

            if isinstance(value, dict):

                unit = str(
                    value.get("unit", "")
                ).strip().lower()

                for nested_key in (
                    "value",
                    "amount",
                    "quantity",
                    "meters",
                    "metres",
                    "distance",
                ):

                    if nested_key not in value:
                        continue

                    converted = convert(
                        value[nested_key]
                    )

                    if converted is None:
                        continue

                    if unit in {
                        "mm",
                        "millimeter",
                        "millimeters",
                    }:
                        return converted / 1000.0

                    if unit in {
                        "cm",
                        "centimeter",
                        "centimeters",
                    }:
                        return converted / 100.0

                    if unit in {
                        "ft",
                        "feet",
                        "foot",
                    }:
                        return converted * 0.3048

                    if unit in {
                        "in",
                        "inch",
                        "inches",
                    }:
                        return converted * 0.0254

                    return converted

                return None

            text = str(
                value
            ).strip().lower()

            # Ratios such as 1:12 are not numeric lengths.
            if ":" in text:
                return None

            match = re.fullmatch(
                r"([-+]?\d+(?:\.\d+)?)"
                r"\s*"
                r"(mm|cm|m|ft|feet|foot|in|inch|inches)?",
                text,
            )

            if not match:
                return None

            number = float(
                match.group(1)
            )

            unit = (
                match.group(2)
                or ""
            )

            if unit == "mm":
                return number / 1000.0

            if unit == "cm":
                return number / 100.0

            if unit in {
                "ft",
                "feet",
                "foot",
            }:
                return number * 0.3048

            if unit in {
                "in",
                "inch",
                "inches",
            }:
                return number * 0.0254

            return number

        for key in keys:

            if key not in result:
                continue

            value = convert(
                result[key]
            )

            if value is not None:
                return value

        return None

    @staticmethod
    def _integer_value(
        result: dict[str, Any],
        *keys: str,
    ) -> int | None:

        for key in keys:

            value = result.get(key)

            if value is None:
                continue

            try:
                return int(value)
            except (
                TypeError,
                ValueError,
            ):
                continue

        return None

    @staticmethod
    def _bool_value(
        result: dict[str, Any],
        *keys: str,
    ) -> bool | None:

        for key in keys:

            if key not in result:
                continue

            value = result[key]

            if isinstance(value, bool):
                return value

            if isinstance(value, str):

                normalized = (
                    value.strip()
                    .lower()
                )

                if normalized in {
                    "true",
                    "yes",
                    "required",
                    "allowed",
                    "permitted",
                }:
                    return True

                if normalized in {
                    "false",
                    "no",
                    "not_required",
                    "prohibited",
                    "not_allowed",
                }:
                    return False

        return None

    @staticmethod
    def _first_bool(
        result: dict[str, Any],
        *keys: str,
    ) -> bool | None:

        return ConstraintCalculator._bool_value(
            result,
            *keys,
        )

    @staticmethod
    def _list_value(
        result: dict[str, Any],
        *keys: str,
    ) -> list[Any]:

        for key in keys:

            value = result.get(key)

            if isinstance(value, list):
                return value

        return []

    # ============================================================
    # VALUE OPERATORS
    # ============================================================

    @staticmethod
    def _max_or_set(
        current: float | None,
        value: float,
    ) -> float:

        if current is None:
            return value

        return max(
            current,
            value,
        )

    @staticmethod
    def _min_or_set(
        current: float | None,
        value: float,
    ) -> float:

        if current is None:
            return value

        return min(
            current,
            value,
        )

    @staticmethod
    def _max_int_or_set(
        current: int | None,
        value: int,
    ) -> int:

        if current is None:
            return value

        return max(
            current,
            value,
        )

    @staticmethod
    def _min_int_or_set(
        current: int | None,
        value: int,
    ) -> int:

        if current is None:
            return value

        return min(
            current,
            value,
        )

    @staticmethod
    def _or_bool(
        current: bool | None,
        value: bool,
    ) -> bool:

        if current is None:
            return value

        return current or value