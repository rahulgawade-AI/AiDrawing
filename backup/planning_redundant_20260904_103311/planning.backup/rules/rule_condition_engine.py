from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ConditionResult:
    status: str
    reason: str = ""

    @property
    def applicable(self) -> bool:
        return self.status == "applicable"

    @property
    def not_applicable(self) -> bool:
        return self.status == "not_applicable"

    @property
    def unresolved(self) -> bool:
        return self.status == "unresolved"


class RuleConditionEngine:
    """
    Production condition evaluator for UDCPR rules.

    Important design principle:

        applicable
        not_applicable
        unresolved

    are deliberately different states.

    An unresolved rule must NEVER be treated as applicable merely
    because the engine does not know the required fact.
    """

    FIELD_ALIASES = {
        # --------------------------------------------------
        # SITE
        # --------------------------------------------------

        "plotArea": "plot_area",
        "plotAreaSqM": "plot_area",
        "plot_area_sqm": "plot_area",
        "plot_area_sq_m": "plot_area",
        "plot_area_sqmt": "plot_area",
        "plot_area_sq_meters": "plot_area",

        # --------------------------------------------------
        # ROAD
        # --------------------------------------------------

        "roadWidth": "road_width",
        "road_width_m": "road_width",
        "road_width_meters": "road_width",
        "access_road_width": "road_width",

        # --------------------------------------------------
        # LOCATION
        # --------------------------------------------------

        "zoneType": "zone_type",
        "landUseZone": "land_use_zone",
        "landUse": "land_use_zone",

        "municipalityName": "municipality",

        "propertyLocation": "location",
        "property_location": "location",

        # --------------------------------------------------
        # BUILDING
        # --------------------------------------------------

        "buildingType": "building_type",
        "buildingUse": "building_use",
        "useType": "building_use",
        "use_type": "building_use",

        "buildingHeight": "building_height",
        "buildingHeightMeters": "building_height",

        "building_height_meters": "building_height",
        "building_height_m": "building_height",

        "numberOfFloors": "number_of_floors",
        "storeys": "number_of_floors",

        # --------------------------------------------------
        # DEVELOPMENT
        # --------------------------------------------------

        "developmentType": "development_type",
        "projectType": "project_type",

        # --------------------------------------------------
        # SPECIAL
        # --------------------------------------------------

        "schemeType": "scheme_type",
        "landUseClassification": "land_use_classification",
    }

    # ======================================================
    # PUBLIC API
    # ======================================================

    def evaluate(
        self,
        condition: dict[str, Any] | None,
        facts: dict[str, Any],
    ) -> ConditionResult:

        if condition is None:
            return ConditionResult(
                "unresolved",
                "Condition is missing.",
            )

        if not isinstance(condition, dict):
            return ConditionResult(
                "unresolved",
                "Condition must be an object.",
            )

        if not condition:
            return ConditionResult(
                "unresolved",
                "Empty condition.",
            )

        return self._evaluate_node(
            condition,
            facts,
        )

    # ======================================================
    # NODE
    # ======================================================

    def _evaluate_node(
        self,
        node: Any,
        facts: dict[str, Any],
    ) -> ConditionResult:

        if not isinstance(node, dict):
            return ConditionResult(
                "unresolved",
                "Unsupported condition structure.",
            )

        condition_type = node.get("type")

        # --------------------------------------------------
        # Explicit universal rule
        # --------------------------------------------------

        if condition_type in {
            "always",
            "always_true",
            "universal",
        }:
            return ConditionResult(
                "applicable",
                "Explicit universal condition.",
            )

        # --------------------------------------------------
        # AND
        # --------------------------------------------------

        if condition_type == "and":

            clauses = (
                node.get("clauses")
                or node.get("operands")
                or node.get("conditions")
            )

            return self._evaluate_and(
                clauses,
                facts,
            )

        # Alternative AND syntax

        if "and" in node:

            return self._evaluate_and(
                node["and"],
                facts,
            )

        if "all" in node:

            return self._evaluate_and(
                node["all"],
                facts,
            )

        # --------------------------------------------------
        # OR
        # --------------------------------------------------

        if condition_type == "or":

            clauses = (
                node.get("clauses")
                or node.get("operands")
                or node.get("conditions")
            )

            return self._evaluate_or(
                clauses,
                facts,
            )

        if "or" in node:

            return self._evaluate_or(
                node["or"],
                facts,
            )

        if "any" in node:

            return self._evaluate_or(
                node["any"],
                facts,
            )

        # --------------------------------------------------
        # NOT
        # --------------------------------------------------

        if condition_type == "not":

            clause = node.get("clause")

            if clause is None:
                return ConditionResult(
                    "unresolved",
                    "NOT clause missing.",
                )

            result = self._evaluate_node(
                clause,
                facts,
            )

            if result.applicable:

                return ConditionResult(
                    "not_applicable",
                    "NOT condition failed.",
                )

            if result.not_applicable:

                return ConditionResult(
                    "applicable",
                    "NOT condition matched.",
                )

            return result

        # --------------------------------------------------
        # BOOLEAN
        # --------------------------------------------------

        if condition_type == "boolean":

            return self._evaluate_boolean(
                node,
                facts,
            )

        # --------------------------------------------------
        # MEASUREMENT
        #
        # Example:
        #
        # {
        #   "type": "measurement",
        #   "field": "building_height",
        #   "unit": "meter"
        # }
        # --------------------------------------------------

        if condition_type == "measurement":

            field = node.get("field")

            if not field:

                return ConditionResult(
                    "unresolved",
                    "Measurement field missing.",
                )

            value = self._get_fact(
                facts,
                field,
            )

            if value is None:

                return ConditionResult(
                    "unresolved",
                    f"Missing fact: {field}",
                )

            return ConditionResult(
                "applicable",
                f"Measurement resolved: {field}.",
            )

        # --------------------------------------------------
        # GENERIC MAPPING
        # --------------------------------------------------

        return self._evaluate_mapping(
            node,
            facts,
        )

    # ======================================================
    # AND
    # ======================================================

    def _evaluate_and(
        self,
        clauses: Any,
        facts: dict[str, Any],
    ) -> ConditionResult:

        if not isinstance(
            clauses,
            list,
        ):

            return ConditionResult(
                "unresolved",
                "AND clauses are invalid.",
            )

        if not clauses:

            return ConditionResult(
                "unresolved",
                "AND condition has no valid clauses.",
            )

        unresolved = []

        for clause in clauses:

            result = self._evaluate_node(
                clause,
                facts,
            )

            if result.not_applicable:

                return result

            if result.unresolved:

                unresolved.append(
                    result.reason
                )

        if unresolved:

            return ConditionResult(
                "unresolved",
                "; ".join(
                    unresolved
                ),
            )

        return ConditionResult(
            "applicable",
            "All AND conditions matched.",
        )

    # ======================================================
    # OR
    # ======================================================

    def _evaluate_or(
        self,
        clauses: Any,
        facts: dict[str, Any],
    ) -> ConditionResult:

        if not isinstance(
            clauses,
            list,
        ):

            return ConditionResult(
                "unresolved",
                "OR clauses are invalid.",
            )

        if not clauses:

            return ConditionResult(
                "unresolved",
                "OR condition has no valid clauses.",
            )

        unresolved = []

        for clause in clauses:

            result = self._evaluate_node(
                clause,
                facts,
            )

            if result.applicable:

                return result

            if result.unresolved:

                unresolved.append(
                    result.reason
                )

        if unresolved:

            return ConditionResult(
                "unresolved",
                "; ".join(
                    unresolved
                ),
            )

        return ConditionResult(
            "not_applicable",
            "No OR condition matched.",
        )

    # ======================================================
    # BOOLEAN
    # ======================================================

    def _evaluate_boolean(
        self,
        node: dict[str, Any],
        facts: dict[str, Any],
    ) -> ConditionResult:

        operator = node.get(
            "operator"
        )

        operands = node.get(
            "operands"
        )

        if not isinstance(
            operands,
            list,
        ):

            return ConditionResult(
                "unresolved",
                "Boolean operands missing.",
            )

        if len(operands) < 2:

            return ConditionResult(
                "unresolved",
                "Boolean expression needs two operands.",
            )

        left = self._resolve_operand(
            operands[0],
            facts,
        )

        right = self._resolve_operand(
            operands[1],
            facts,
        )

        if left is None:

            return ConditionResult(
                "unresolved",
                "Unable to resolve left operand.",
            )

        if right is None:

            return ConditionResult(
                "unresolved",
                "Unable to resolve right operand.",
            )

        try:

            matched = self._compare(
                left,
                operator,
                right,
            )

        except (
            TypeError,
            ValueError,
        ):

            return ConditionResult(
                "unresolved",
                (
                    "Cannot compare "
                    f"{left!r} "
                    f"{operator} "
                    f"{right!r}"
                ),
            )

        if matched:

            return ConditionResult(
                "applicable",
                (
                    f"{left!r} "
                    f"{operator} "
                    f"{right!r}"
                ),
            )

        return ConditionResult(
            "not_applicable",
            (
                f"{left!r} "
                f"{operator} "
                f"{right!r}"
            ),
        )

    # ======================================================
    # MAPPING
    # ======================================================

    def _evaluate_mapping(
        self,
        node: dict[str, Any],
        facts: dict[str, Any],
    ) -> ConditionResult:

        results = []

        ignored = {
            "type",
            "operator",
            "operands",
            "clauses",
            "conditions",
            "and",
            "or",
            "all",
            "any",
        }

        for raw_field, expression in node.items():

            if raw_field in ignored:
                continue

            field = self._canonical_field(
                raw_field
            )

            # ----------------------------------------------
            # field_min
            # ----------------------------------------------

            if raw_field.endswith(
                "_min"
            ):

                base_field = raw_field[
                    :-4
                ]

                actual = self._get_fact(
                    facts,
                    base_field,
                )

                if actual is None:

                    return ConditionResult(
                        "unresolved",
                        f"Missing fact: {base_field}",
                    )

                expected = (
                    self._normalize_value(
                        expression
                    )
                )

                if expected is None:

                    return ConditionResult(
                        "unresolved",
                        f"Invalid minimum: {raw_field}",
                    )

                return self._comparison_result(
                    base_field,
                    actual,
                    ">=",
                    expected,
                )

            # ----------------------------------------------
            # field_max
            # ----------------------------------------------

            if raw_field.endswith(
                "_max"
            ):

                base_field = raw_field[
                    :-4
                ]

                actual = self._get_fact(
                    facts,
                    base_field,
                )

                if actual is None:

                    return ConditionResult(
                        "unresolved",
                        f"Missing fact: {base_field}",
                    )

                expected = (
                    self._normalize_value(
                        expression
                    )
                )

                if expected is None:

                    return ConditionResult(
                        "unresolved",
                        f"Invalid maximum: {raw_field}",
                    )

                return self._comparison_result(
                    base_field,
                    actual,
                    "<=",
                    expected,
                )

            # ----------------------------------------------
            # Nested expression
            # ----------------------------------------------

            if isinstance(
                expression,
                dict,
            ):

                actual = self._get_fact(
                    facts,
                    field,
                )

                if actual is None:

                    return ConditionResult(
                        "unresolved",
                        f"Missing fact: {field}",
                    )

                operator = (
                    self._extract_operator(
                        expression
                    )
                )

                expected = self._extract_expected_value(
                    expression,
                    operator,
                )

                if expected is None:

                    return ConditionResult(
                        "unresolved",
                        (
                            f"Missing comparison "
                            f"value for {field}."
                        ),
                    )

                result = (
                    self._comparison_result(
                        field,
                        actual,
                        operator,
                        expected,
                    )
                )

                if result.not_applicable:

                    return result

                if result.unresolved:

                    return result

                results.append(
                    result
                )

                continue

            # ----------------------------------------------
            # Direct equality
            # ----------------------------------------------

            actual = self._get_fact(
                facts,
                field,
            )

            if actual is None:

                return ConditionResult(
                    "unresolved",
                    f"Missing fact: {field}",
                )

            expected = (
                self._normalize_value(
                    expression
                )
            )

            result = (
                self._comparison_result(
                    field,
                    actual,
                    "==",
                    expected,
                )
            )

            if result.not_applicable:

                return result

            if result.unresolved:

                return result

            results.append(
                result
            )

        if not results:

            return ConditionResult(
                "unresolved",
                "No evaluable conditions.",
            )

        return ConditionResult(
            "applicable",
            "All conditions matched.",
        )




    def _extract_expected_value(
        self,
        expression: dict[str, Any],
        operator: str,
    ) -> Any:
        """
        Extract the expected comparison value from a rule expression.

        Supports both:

            {"operator": ">", "value": 52.5}

        and compact UDCPR forms:

            {"greater_than": 52.5}
            {"less_than": 1000}
            {"greaterThan": 18}
            {"lessThanOrEqual": 52.5}
        """

        # Explicit operator/value syntax
        if "value" in expression:
            return self._normalize_value(
                expression["value"]
            )

        # Operator expressed as a key
        operator_keys = {
            ">": (
                "greaterThan",
                "greater_than",
            ),
            ">=": (
                "greaterThanOrEqual",
                "greaterThanEqual",
                "greater_than_or_equal",
                "greater_than_equal",
            ),
            "<": (
                "lessThan",
                "less_than",
            ),
            "<=": (
                "lessThanOrEqual",
                "lessThanEqual",
                "less_than_or_equal",
                "less_than_equal",
            ),
            "==": (
                "equals",
                "equal",
            ),
            "!=": (
                "notEquals",
                "not_equals",
            ),
            "in": (
                "in",
            ),
            "not_in": (
                "notIn",
                "not_in",
            ),
        }

        for key in operator_keys.get(operator, ()):
            if key in expression:
                return self._normalize_value(
                    expression[key]
                )

        return None





    # ======================================================
    # OPERATOR EXTRACTION
    # ======================================================

    def _extract_operator(
        self,
        expression: dict[str, Any],
    ) -> str:

        if "operator" in expression:

            return str(
                expression["operator"]
            )

        if "greaterThan" in expression:
             return ">"

        if "greater_than" in expression:
            return ">"

        if "greaterThanOrEqual" in expression:
            return ">="

        if "greater_than_or_equal" in expression:
            return ">="

        if "greaterThanEqual" in expression:
            return ">="

        if "greater_than_equal" in expression:
            return ">="

        if "lessThan" in expression:
            return "<"

        if "less_than" in expression:
            return "<"

        if "lessThanOrEqual" in expression:
            return "<="

        if "less_than_or_equal" in expression:
            return "<="

        if "lessThanEqual" in expression:
            return "<="

        if "less_than_equal" in expression:
            return "<="

        if "minimum" in expression:
            return ">="

        if "min" in expression:
            return ">="

        if "maximum" in expression:
            return "<="

        if "max" in expression:
            return "<="

        if "equals" in expression:
            return "=="

        if "equal" in expression:
            return "=="

        if "notEquals" in expression:
            return "!="

        if "in" in expression:
            return "in"

        if "notIn" in expression:
            return "not_in"

        return "=="

    # ======================================================
    # VALUE NORMALIZATION
    # ======================================================

    def _normalize_value(
        self,
        value: Any,
    ) -> Any:

        if isinstance(
            value,
            dict,
        ):

            # ----------------------------------------------
            # quantity
            # ----------------------------------------------

            if "quantity" in value:

                return self._convert_unit(
                    value["quantity"],
                    value.get("unit"),
                )

            # ----------------------------------------------
            # amount
            # ----------------------------------------------

            if "amount" in value:

                return self._convert_unit(
                    value["amount"],
                    value.get("unit"),
                )

            # ----------------------------------------------
            # value + unit
            # ----------------------------------------------

            if "value" in value:

                return self._convert_unit(
                    value["value"],
                    value.get("unit"),
                )

            # ----------------------------------------------
            # membership operators
            # ----------------------------------------------

            if "in" in value:

                return [
                    self._normalize_value(item)
                    for item in value["in"]
                ]

            if "notIn" in value:

                return [
                    self._normalize_value(item)
                    for item in value["notIn"]
                ]

            if "not_in" in value:

                return [
                    self._normalize_value(item)
                    for item in value["not_in"]
                ]

           
            # ----------------------------------------------
            # meters
            # ----------------------------------------------

            if "meters" in value:

                return float(
                    value["meters"]
                )

            if "meter" in value:

                return float(
                    value["meter"]
                )

            if "m" in value:

                return float(
                    value["m"]
                )

            # ----------------------------------------------
            # square meters
            # ----------------------------------------------

            if "sq_m" in value:

                return float(
                    value["sq_m"]
                )

            if "sqm" in value:

                return float(
                    value["sqm"]
                )

            # ----------------------------------------------
            # number
            # ----------------------------------------------

            if "number" in value:

                return value["number"]

            # ----------------------------------------------
            # Operator-specific object
            # ----------------------------------------------

            for key in (
                "greaterThan",
                "greaterThanOrEqual",
                "lessThan",
                "lessThanOrEqual",
                "minimum",
                "maximum",
                "min",
                "max",
            ):

                if key in value:

                    return (
                        self._normalize_value(
                            value[key]
                        )
                    )

            return None

        return value

    # ======================================================
    # UNIT CONVERSION
    # ======================================================

    def _convert_unit(
        self,
        value: Any,
        unit: str | None,
    ) -> Any:

        if value is None:
            return None

        try:
            numeric = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return value

        if unit is None:
            return numeric

        normalized = (
            str(unit)
            .strip()
            .lower()
            .replace("²", "2")
            .replace(" ", "")
        )

        # ----------------------------------------------
        # Length
        # ----------------------------------------------

        if normalized in {
            "m",
            "meter",
            "meters",
            "metre",
            "metres",
        }:

            return numeric

        if normalized in {
            "cm",
            "centimeter",
            "centimeters",
        }:

            return numeric / 100.0

        if normalized in {
            "mm",
            "millimeter",
            "millimeters",
        }:

            return numeric / 1000.0

        if normalized in {
            "ft",
            "feet",
            "foot",
        }:

            return numeric * 0.3048

        # ----------------------------------------------
        # Area
        # ----------------------------------------------

        if normalized in {
            "sqm",
            "sq.m",
            "sq.m.",
            "m2",
            "m^2",
            "squaremeter",
            "squaremeters",
        }:

            return numeric

        if normalized in {
            "sqft",
            "sq.ft",
            "sq.ft.",
            "ft2",
            "squarefeet",
        }:

            return numeric * 0.09290304

        if normalized in {
            "ha",
            "hectare",
            "hectares",
        }:

            return numeric * 10000.0

        # Maharashtra land-area terminology
        if normalized in {
            "guntha",
            "gunthas",
        }:

            return numeric * 101.17141056

        return numeric

    # ======================================================
    # FACT RESOLUTION
    # ======================================================

    def _get_fact(
        self,
        facts: dict[str, Any],
        field: str,
    ) -> Any:

        canonical = (
            self._canonical_field(
                field
            )
        )

        # Direct canonical value

        if canonical in facts:

            value = facts[canonical]

            if value is not None:

                return self._normalize_fact(
                    value
                )

        # Original field

        if field in facts:

            value = facts[field]

            if value is not None:

                return self._normalize_fact(
                    value
                )

        # Alias lookup

        for alias, target in (
            self.FIELD_ALIASES.items()
        ):

            if (
                target == canonical
                and alias in facts
            ):

                value = facts[alias]

                if value is not None:

                    return self._normalize_fact(
                        value
                    )

        # Nested field

        current: Any = facts

        for part in field.split("."):

            if isinstance(
                current,
                dict,
            ):

                if part not in current:

                    return None

                current = current[part]

            else:

                if not hasattr(
                    current,
                    part,
                ):

                    return None

                current = getattr(
                    current,
                    part,
                )

        if current is None:
            return None

        return self._normalize_fact(
            current
        )

    def _normalize_fact(
        self,
        value: Any,
    ) -> Any:

        if isinstance(
            value,
            dict,
        ):

            normalized = (
                self._normalize_value(
                    value
                )
            )

            if normalized is not None:

                return normalized

        return value

    # ======================================================
    # OPERAND
    # ======================================================

    def _resolve_operand(
        self,
        operand: Any,
        facts: dict[str, Any],
    ) -> Any:

        if isinstance(
            operand,
            (int, float, bool),
        ):

            return operand

        if isinstance(
            operand,
            str,
        ):

            fact = self._get_fact(
                facts,
                operand,
            )

            if fact is not None:

                return fact

            return operand

        if isinstance(
            operand,
            dict,
        ):

            field = operand.get(
                "field"
            )

            if field:

                value = self._get_fact(
                    facts,
                    field,
                )

                if value is not None:

                    return value

            return self._normalize_value(
                operand
            )

        return None

    # ======================================================
    # COMPARISON
    # ======================================================

    def _comparison_result(
        self,
        field: str,
        actual: Any,
        operator: str,
        expected: Any,
    ) -> ConditionResult:

        actual = self._normalize_value(
            actual
        )

        expected = self._normalize_value(
            expected
        )

        try:

            matched = self._compare(
                actual,
                operator,
                expected,
            )

        except (
            TypeError,
            ValueError,
        ):

            return ConditionResult(
                "unresolved",
                (
                    f"Cannot compare "
                    f"{field}: "
                    f"{actual!r} "
                    f"{operator} "
                    f"{expected!r}"
                ),
            )

        reason = (
            f"{field}: "
            f"{actual!r} "
            f"{operator} "
            f"{expected!r}"
        )

        if matched:

            return ConditionResult(
                "applicable",
                reason,
            )

        return ConditionResult(
            "not_applicable",
            reason,
        )

    # ======================================================
    # COMPARE
    # ======================================================

    def _compare(
        self,
        actual: Any,
        operator: str,
        expected: Any,
    ) -> bool:

        operator = (
            str(operator)
            .strip()
            .lower()
        )

        if operator in {
            "=",
            "==",
            "equals",
            "equal",
        }:

            return self._equal(
                actual,
                expected,
            )

        if operator in {
            "!=",
            "not_equals",
            "not_equal",
        }:

            return not self._equal(
                actual,
                expected,
            )

        if operator == ">":

            return actual > expected

        if operator == ">=":

            return actual >= expected

        if operator == "<":

            return actual < expected

        if operator == "<=":

            return actual <= expected

        if operator == "in":

            if not isinstance(
                expected,
                (
                    list,
                    tuple,
                    set,
                ),
            ):

                return False

            return any(
                self._equal(
                    actual,
                    item,
                )
                for item in expected
            )

        if operator == "not_in":

            if not isinstance(
                expected,
                (
                    list,
                    tuple,
                    set,
                ),
            ):

                return False

            return not any(
                self._equal(
                    actual,
                    item,
                )
                for item in expected
            )

        if operator in {
            "contains",
            "includes",
        }:

            if isinstance(
                actual,
                (
                    list,
                    tuple,
                    set,
                ),
            ):

                return any(
                    self._equal(
                        item,
                        expected,
                    )
                    for item in actual
                )

            if isinstance(
                actual,
                str,
            ):

                return (
                    str(expected).lower()
                    in actual.lower()
                )

            return False

        raise ValueError(
            f"Unsupported operator: {operator}"
        )

    # ======================================================
    # EQUALITY
    # ======================================================

    @staticmethod
    def _equal(
        actual: Any,
        expected: Any,
    ) -> bool:

        if (
            isinstance(
                actual,
                str,
            )
            and isinstance(
                expected,
                str,
            )
        ):

            return (
                actual.strip().lower()
                ==
                expected.strip().lower()
            )

        return actual == expected

    # ======================================================
    # FIELD
    # ======================================================

    def _canonical_field(
        self,
        field: str,
    ) -> str:

        return self.FIELD_ALIASES.get(
            field,
            field,
        )