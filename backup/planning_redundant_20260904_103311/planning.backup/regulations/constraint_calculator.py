from __future__ import annotations

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


class ConstraintCalculator:
    """
    Converts applicable UDCPR rules into PlanningConstraints.

    This class does NOT decide whether a rule applies.
    Rule applicability is handled by the rule engine/resolver.

    Responsibilities:
        - read applicable rule results
        - populate regulatory constraints
        - calculate derived values such as maximum built-up area
        - preserve rule traceability
        - never invent unsupported regulatory values
    """

    def calculate(
        self,
        facts: PlanningFacts,
        rules: list[ApplicableRule],
    ) -> PlanningConstraints:

        constraints = PlanningConstraints()

        applicable = [
            rule
            for rule in rules
            if getattr(rule, "status", None) == "applicable"
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
            in {
                "not_applicable",
                "invalid",
            }
        ]

        constraints.applied_rules = applicable
        constraints.unresolved_rules = unresolved
        constraints.rejected_rules = rejected

        # --------------------------------------------------
        # Apply individual rules
        # --------------------------------------------------

        for rule in applicable:
            self._apply_rule(
                constraints=constraints,
                rule=rule,
            )

        # --------------------------------------------------
        # Derived calculations
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Audit
        # --------------------------------------------------

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

    # ======================================================
    # RULE APPLICATION
    # ======================================================

    def _apply_rule(
        self,
        constraints: PlanningConstraints,
        rule: ApplicableRule,
    ) -> None:

        category = (
            rule.category or ""
        ).strip().lower()

        name = (
            rule.name or ""
        ).strip().lower()

        result = rule.result or {}

        # --------------------------------------------------
        # Land use
        # --------------------------------------------------

        self._apply_land_use(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------
        # FSI
        # --------------------------------------------------

        self._apply_fsi(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------
        # Setbacks / coverage
        # --------------------------------------------------

        self._apply_setbacks(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------
        # Height
        # --------------------------------------------------

        self._apply_height(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------
        # Parking
        # --------------------------------------------------

        self._apply_parking(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------
        # Fire
        # --------------------------------------------------

        self._apply_fire(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------
        # Circulation
        # --------------------------------------------------

        self._apply_circulation(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------
        # Accessibility
        # --------------------------------------------------

        self._apply_accessibility(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------
        # Open spaces
        # --------------------------------------------------

        self._apply_open_spaces(
            constraints,
            category,
            name,
            result,
        )

        # --------------------------------------------------
        # Special conditions
        # --------------------------------------------------

        self._apply_special_conditions(
            constraints,
            category,
            name,
            result,
        )

    # ======================================================
    # LAND USE
    # ======================================================

    def _apply_land_use(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        if category == "building type":
            permitted = self._list_value(
                result,
                "permitted_uses",
                "uses",
                "permittedUses",
            )

            if permitted:
                for use in permitted:
                    if use not in constraints.permitted_uses:
                        constraints.permitted_uses.append(
                            str(use)
                        )

        if (
            "mixed use" in name
            or "mixed use" in category
        ):
            value = self._bool_value(
                result,
                "allowed",
                "permitted",
                "mixed_use_allowed",
            )

            if value is not None:
                constraints.mixed_use_allowed = value

    # ======================================================
    # FSI
    # ======================================================

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

    # ======================================================
    # SETBACKS / COVERAGE
    # ======================================================

    def _apply_setbacks(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        front = self._number_value(
            result,
            "front_setback",
            "frontMargin",
            "front_margin",
            "minimum_front_margin",
        )

        rear = self._number_value(
            result,
            "rear_setback",
            "rearMargin",
            "rear_margin",
            "minimum_rear_margin",
        )

        side = self._number_value(
            result,
            "side_setback",
            "sideMargin",
            "side_margin",
            "minimum_side_margin",
        )

        left = self._number_value(
            result,
            "side_setback_left",
            "left_side_margin",
        )

        right = self._number_value(
            result,
            "side_setback_right",
            "right_side_margin",
        )

        coverage = self._number_value(
            result,
            "maximum_ground_coverage",
            "ground_coverage",
            "maximum_coverage",
            "coverage",
        )

        open_space = self._number_value(
            result,
            "minimum_open_space",
            "minimum_open_space_m2",
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

        if side is not None:
            constraints.side_setback_left = (
                self._max_or_set(
                    constraints.side_setback_left,
                    side,
                )
            )

            constraints.side_setback_right = (
                self._max_or_set(
                    constraints.side_setback_right,
                    side,
                )
            )

        if left is not None:
            constraints.side_setback_left = (
                self._max_or_set(
                    constraints.side_setback_left,
                    left,
                )
            )

        if right is not None:
            constraints.side_setback_right = (
                self._max_or_set(
                    constraints.side_setback_right,
                    right,
                )
            )

        if coverage is not None:
            constraints.maximum_ground_coverage = (
                self._min_or_set(
                    constraints.maximum_ground_coverage,
                    coverage,
                )
            )

        if open_space is not None:
            constraints.minimum_open_space = (
                self._max_or_set(
                    constraints.minimum_open_space,
                    open_space,
                )
            )

    # ======================================================
    # HEIGHT
    # ======================================================

    def _apply_height(
        self,
        constraints: PlanningConstraints,
        category: str,
        name: str,
        result: dict[str, Any],
    ) -> None:

        height = self._number_value(
            result,
            "maximum_height_m",
            "maximum_height",
            "max_height",
            "height_limit",
            "heightLimit",
            "permissible_height",
        )

        storeys = self._integer_value(
            result,
            "maximum_storeys",
            "max_storeys",
            "permissible_storeys",
            "storeys",
            "floors",
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
                    storeys,
                )
            )

    # ======================================================
    # PARKING
    # ======================================================

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

    # ======================================================
    # FIRE
    # ======================================================

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

        if fire_access is not None:
            constraints.fire_access_required = (
                self._or_bool(
                    constraints.fire_access_required,
                    fire_access,
                )
            )

        if fire_lift is not None:
            constraints.fire_lift_required = (
                self._or_bool(
                    constraints.fire_lift_required,
                    fire_lift,
                )
            )

        if fire_stair is not None:
            constraints.fire_staircase_required = (
                self._or_bool(
                    constraints.fire_staircase_required,
                    fire_stair,
                )
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

    # ======================================================
    # CIRCULATION
    # ======================================================

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
            constraints.lift_required = (
                self._or_bool(
                    constraints.lift_required,
                    lift,
                )
            )

        if lift_count is not None:
            constraints.lift_count = (
                self._max_int_or_set(
                    constraints.lift_count,
                    lift_count,
                )
            )

    # ======================================================
    # ACCESSIBILITY
    # ======================================================

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

    # ======================================================
    # OPEN SPACE
    # ======================================================

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

    # ======================================================
    # SPECIAL CONDITIONS
    # ======================================================

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
            constraints.road_widening = (
                self._or_bool(
                    constraints.road_widening,
                    road_widening,
                )
            )

        if reservation is not None:
            constraints.reservation_present = (
                self._or_bool(
                    constraints.reservation_present,
                    reservation,
                )
            )

        if special_height is not None:
            constraints.special_height_limit_m = (
                self._min_or_set(
                    constraints.special_height_limit_m,
                    special_height,
                )
            )

    # ======================================================
    # DERIVED FSI
    # ======================================================

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

        # A maximum FSI is only a regulatory ceiling.  It must never
        # become the achieved/permissible FSI by itself.  Additional FSI
        # must come from an applicable rule result.

    # ======================================================
    # BUILT-UP AREA
    # ======================================================

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

    # ======================================================
    # HEIGHT
    # ======================================================

    def _calculate_height(
        self,
        facts: PlanningFacts,
        constraints: PlanningConstraints,
    ) -> None:

        # A special height restriction is another
        # upper bound, never an override.
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

        # If a rule provides storeys and a floor height
        # is available, derive a physical height.
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

    # ======================================================
    # VALUE HELPERS
    # ======================================================

    @staticmethod
    def _number_value(
        result: dict[str, Any],
        *keys: str,
    ) -> float | None:

        for key in keys:
            value = result.get(key)
    
            if value is None:
                continue
            
            # Direct numeric value
            if isinstance(value, (int, float)):
                return float(value)
    
            # UDCPR structured numeric value
            #
            # Examples:
            # {"value": 1.0}
            # {"amount": 3.0}
            # {"quantity": 1.5}
            if isinstance(value, dict):
            
                for nested_key in (
                    "value",
                    "amount",
                    "quantity",
                ):
                    nested_value = value.get(nested_key)
    
                    if nested_value is None:
                        continue
                    
                    try:
                        return float(nested_value)
                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue
                    
            # Numeric strings
            try:
                return float(value)
            except (
                TypeError,
                ValueError,
            ):
                continue
            
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
                normalized = value.strip().lower()

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
    def _list_value(
        result: dict[str, Any],
        *keys: str,
    ) -> list[Any]:

        for key in keys:
            value = result.get(key)

            if isinstance(value, list):
                return value

        return []

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