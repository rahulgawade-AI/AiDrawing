from __future__ import annotations

from typing import Any


class RuleEvaluator:
    """
    Evaluates the JSON condition structure stored
    in the UDCPR RuleModel.condition_json field.

    Supported operators:

        =
        ==
        !=
        >
        >=
        <
        <=
        in
        not_in
        contains
        exists
        between

    Supported logical structures:

        and
        or
        not

    The evaluator deliberately contains NO LLM logic.

    Regulatory evaluation must remain deterministic.
    """

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def evaluate(
        self,
        condition: dict[str, Any] | None,
        facts: Any,
    ) -> bool:

        if not condition:
            return True

        if not isinstance(
            condition,
            dict,
        ):
            return False

        # --------------------------------------------------
        # Explicit logical operators
        # --------------------------------------------------

        if "type" in condition:

            condition_type = str(
                condition["type"]
            ).lower()

            if condition_type in {
                "always",
                "always_true",
            }:
                return True

            if condition_type in {
                "and",
            }:
                conditions = condition.get(
                    "conditions",
                    [],
                )

                return all(
                    self.evaluate(
                        item,
                        facts,
                    )
                    for item in conditions
                )

            if condition_type == "or":

                conditions = condition.get(
                    "conditions",
                    [],
                )

                return any(
                    self.evaluate(
                        item,
                        facts,
                    )
                    for item in conditions
                )

            if condition_type == "not":

                nested = condition.get(
                    "condition"
                )

                return not self.evaluate(
                    nested,
                    facts,
                )

            if condition_type == "presence":

                field = condition.get(
                    "field"
                )

                return self._get(
                    facts,
                    field,
                ) is not None

        # --------------------------------------------------
        # Conventional field/operator/value
        # --------------------------------------------------

        field = condition.get(
            "field"
        )

        operator = condition.get(
            "operator"
        )

        value = condition.get(
            "value"
        )

        if field is not None:

            actual = self._get(
                facts,
                field,
            )

            return self._compare(
                actual,
                operator,
                value,
            )

        # --------------------------------------------------
        # Shorthand field conditions
        # --------------------------------------------------

        for key, expected in condition.items():

            if key in {
                "type",
                "conditions",
            }:
                continue

            actual = self._get(
                facts,
                key,
            )

            if isinstance(
                expected,
                dict,
            ):
                if not self._evaluate_nested(
                    actual,
                    expected,
                ):
                    return False

            elif isinstance(
                expected,
                list,
            ):
                if not self._contains_match(
                    actual,
                    expected,
                ):
                    return False

            else:
                if not self._equal(
                    actual,
                    expected,
                ):
                    return False

        return True

    # --------------------------------------------------
    # Field lookup
    # --------------------------------------------------

    def _get(
        self,
        facts: Any,
        field: str | None,
    ) -> Any:

        if not field:
            return None

        if hasattr(
            facts,
            "get",
        ):
            return facts.get(
                field
            )

        if isinstance(
            facts,
            dict,
        ):
            return facts.get(
                field
            )

        return getattr(
            facts,
            field,
            None,
        )

    # --------------------------------------------------
    # Comparison
    # --------------------------------------------------

    def _compare(
        self,
        actual: Any,
        operator: str | None,
        expected: Any,
    ) -> bool:

        if operator is None:

            return self._equal(
                actual,
                expected,
            )

        operator = str(
            operator
        ).lower()

        if operator in {
            "=",
            "==",
            "eq",
        }:
            return self._equal(
                actual,
                expected,
            )

        if operator in {
            "!=",
            "ne",
        }:
            return not self._equal(
                actual,
                expected,
            )

        if operator == ">":
            return self._numeric_compare(
                actual,
                expected,
                lambda a, b: a > b,
            )

        if operator == ">=":
            return self._numeric_compare(
                actual,
                expected,
                lambda a, b: a >= b,
            )

        if operator == "<":
            return self._numeric_compare(
                actual,
                expected,
                lambda a, b: a < b,
            )

        if operator == "<=":
            return self._numeric_compare(
                actual,
                expected,
                lambda a, b: a <= b,
            )

        if operator == "in":

            if isinstance(
                expected,
                (list, tuple, set),
            ):
                return self._contains_match(
                    actual,
                    expected,
                )

            return self._equal(
                actual,
                expected,
            )

        if operator in {
            "not_in",
            "not in",
        }:

            return not self._compare(
                actual,
                "in",
                expected,
            )

        if operator == "contains":

            if isinstance(
                actual,
                (list, tuple, set, str),
            ):
                return expected in actual

            return False

        if operator == "exists":

            expected_bool = bool(
                expected
            )

            exists = (
                actual is not None
            )

            return exists == expected_bool

        if operator == "between":

            if not isinstance(
                expected,
                (list, tuple),
            ):
                return False

            if len(expected) != 2:
                return False

            return self._numeric_compare(
                actual,
                expected[0],
                lambda a, b: a >= b,
            ) and self._numeric_compare(
                actual,
                expected[1],
                lambda a, b: a <= b,
            )

        return False

    # --------------------------------------------------
    # Nested structures
    # --------------------------------------------------

    def _evaluate_nested(
        self,
        actual: Any,
        condition: dict[str, Any],
    ) -> bool:

        if (
            "greaterThan"
            in condition
        ):

            return self._numeric_compare(
                actual,
                condition[
                    "greaterThan"
                ],
                lambda a, b: a > b,
            )

        if (
            "greaterThanOrEqual"
            in condition
        ):

            return self._numeric_compare(
                actual,
                condition[
                    "greaterThanOrEqual"
                ],
                lambda a, b: a >= b,
            )

        if (
            "lessThan"
            in condition
        ):

            return self._numeric_compare(
                actual,
                condition[
                    "lessThan"
                ],
                lambda a, b: a < b,
            )

        if (
            "lessThanOrEqual"
            in condition
        ):

            return self._numeric_compare(
                actual,
                condition[
                    "lessThanOrEqual"
                ],
                lambda a, b: a <= b,
            )

        if "value" in condition:

            return self._equal(
                actual,
                condition["value"],
            )

        if "in" in condition:

            return self._compare(
                actual,
                "in",
                condition["in"],
            )

        return False

    # --------------------------------------------------
    # Numeric comparison
    # --------------------------------------------------

    def _numeric_compare(
        self,
        actual: Any,
        expected: Any,
        operation,
    ) -> bool:

        actual_number = self._number(
            actual
        )

        expected_number = self._number(
            expected
        )

        if (
            actual_number is None
            or expected_number is None
        ):
            return False

        try:
            return operation(
                actual_number,
                expected_number,
            )
        except Exception:
            return False

    # --------------------------------------------------
    # Number conversion
    # --------------------------------------------------

    @staticmethod
    def _number(
        value: Any,
    ) -> float | None:

        if isinstance(
            value,
            bool,
        ):
            return None

        if isinstance(
            value,
            (int, float),
        ):
            return float(
                value
            )

        if isinstance(
            value,
            str,
        ):

            try:
                return float(
                    value.strip()
                )
            except ValueError:
                return None

        if isinstance(
            value,
            dict,
        ):

            if "value" in value:
                return RuleEvaluator._number(
                    value["value"]
                )

        return None

    # --------------------------------------------------
    # Equality
    # --------------------------------------------------

    def _equal(
        self,
        actual: Any,
        expected: Any,
    ) -> bool:

        if actual is None:
            return False

        actual_number = self._number(
            actual
        )

        expected_number = self._number(
            expected
        )

        if (
            actual_number is not None
            and expected_number is not None
        ):
            return (
                actual_number
                == expected_number
            )

        if isinstance(
            actual,
            str,
        ) and isinstance(
            expected,
            str,
        ):

            return (
                actual.strip().lower()
                ==
                expected.strip().lower()
            )

        return actual == expected

    # --------------------------------------------------
    # List matching
    # --------------------------------------------------

    def _contains_match(
        self,
        actual: Any,
        expected: Any,
    ) -> bool:

        if not isinstance(
            expected,
            (list, tuple, set),
        ):
            expected = [
                expected
            ]

        if isinstance(
            actual,
            (list, tuple, set),
        ):

            return any(
                self._equal(
                    item,
                    candidate,
                )
                for item in actual
                for candidate in expected
            )

        return any(
            self._equal(
                actual,
                candidate,
            )
            for candidate in expected
        )