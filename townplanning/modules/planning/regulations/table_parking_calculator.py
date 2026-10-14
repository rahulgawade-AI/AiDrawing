"""
Deterministic parking calculation from persisted UDCPR tables.

Uses PostgreSQL Table No.8-B - Parking Requirements.

No LLM is used.

The calculator reads the existing ExtractedTable representation and
converts the residential multi-family parking rows into deterministic
parking requirements.
"""

from __future__ import annotations

import math
import re
from typing import Any


class TableParkingCalculator:

    TABLE_8B_MARKERS = (
        "table no.8-b",
        "parking requirements",
    )

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def calculate(
        self,
        table,
        facts,
    ) -> dict[str, Any]:

        if table is None:
            return {}

        if not self._is_table_8b(table):
            return {}

        unit_mix = self._get_unit_mix(
            facts
        )

        if not unit_mix:
            return {
                "status": "insufficient_facts",
                "reason": (
                    "Table 8-B parking requires residential "
                    "tenement count and carpet area."
                ),
                "table_id": str(
                    getattr(table, "id", "")
                ),
                "table_page": getattr(
                    table,
                    "page",
                    None,
                ),
            }

        congested = self._is_congested(
            facts
        )

        car_total = 0.0
        two_wheeler_total = 0.0

        applied_rules = []

        for unit in unit_mix:

            units = self._number(
                unit.get("units")
                or unit.get("count")
                or unit.get("quantity")
            )

            carpet_area = self._number(
                unit.get("carpet_area")
                or unit.get("carpetArea")
                or unit.get("area")
            )

            if units is None or units <= 0:
                continue

            if carpet_area is None:
                continue

            rule = self._find_residential_rule(
                table,
                carpet_area,
            )

            if rule is None:
                continue

            divisor = rule["divisor"]

            car_rate = (
                rule["congested_car"]
                if congested
                else rule["non_congested_car"]
            )

            scooter_rate = (
                rule["congested_scooter"]
                if congested
                else rule["non_congested_scooter"]
            )

            car_spaces = (
                units / divisor
            ) * car_rate

            scooter_spaces = (
                units / divisor
            ) * scooter_rate

            car_total += car_spaces
            two_wheeler_total += scooter_spaces

            applied_rules.append(
                {
                    "bhk": unit.get("bhk")
                    or unit.get("type")
                    or unit.get("name"),

                    "units": units,

                    "carpet_area": carpet_area,

                    "divisor": divisor,

                    "car_spaces_per_group": car_rate,

                    "two_wheeler_spaces_per_group": scooter_rate,

                    "car_spaces": car_spaces,

                    "two_wheeler_spaces": scooter_spaces,

                    "rule_text": rule["rule_text"],
                }
            )

        if not applied_rules:

            return {
                "status": "insufficient_facts",
                "reason": (
                    "No Table 8-B residential parking row "
                    "could be matched to the supplied unit "
                    "carpet areas."
                ),
                "table_id": str(
                    getattr(table, "id", "")
                ),
                "table_page": getattr(
                    table,
                    "page",
                    None,
                ),
            }

        # UDCPR Table 8-B:
        #
        # "In addition 5% visitor parking"
        #
        # Apply 5% to the calculated car parking.
        visitor_parking = (
            car_total * 0.05
        )

        # Parking spaces are whole spaces.
        car_required = math.ceil(
            car_total
        )

        two_wheeler_required = math.ceil(
            two_wheeler_total
        )

        visitor_required = math.ceil(
            visitor_parking
        )

        return {
            "status": "calculated",

            "source": {
                "table": "Table No.8-B",
                "page": getattr(
                    table,
                    "page",
                    None,
                ),
                "table_index": getattr(
                    table,
                    "index",
                    None,
                ),
                "table_id": str(
                    getattr(table, "id", "")
                ),
            },

            "area_classification": (
                "congested"
                if congested
                else "non_congested"
            ),

            "car_parking_required": (
                car_required
            ),

            "two_wheeler_parking_required": (
                two_wheeler_required
            ),

            "visitor_parking_required": (
                visitor_required
            ),

            "parking_calculation": {
                "car_raw": car_total,
                "two_wheeler_raw": two_wheeler_total,
                "visitor_raw": visitor_parking,
            },

            "applied_rules": applied_rules,
        }

    # ---------------------------------------------------------
    # TABLE IDENTIFICATION
    # ---------------------------------------------------------

    def _is_table_8b(
        self,
        table,
    ) -> bool:

        title = str(
            getattr(
                table,
                "title",
                "",
            )
            or ""
        ).lower()

        headers = " ".join(
            str(value)
            for value in (
                getattr(
                    table,
                    "headers",
                    []
                )
                or []
            )
        ).lower()

        combined = (
            title
            + " "
            + headers
        )

        return (
            "table no.8-b" in combined
            or "parking requirements" in combined
        )

    # ---------------------------------------------------------
    # UNIT MIX
    # ---------------------------------------------------------

    def _get_unit_mix(
        self,
        facts,
    ) -> list[dict[str, Any]]:

        raw = getattr(
            facts,
            "requested_unit_mix",
            None,
        )

        if raw:

            if isinstance(
                raw,
                list,
            ):
                return [
                    item
                    for item in raw
                    if isinstance(
                        item,
                        dict,
                    )
                ]

        # Also support the existing individual BHK
        # fields without changing PlanningFacts.
        result = []

        mappings = (
            (
                "requested_1bhk_units",
                "1BHK",
            ),
            (
                "requested_2bhk_units",
                "2BHK",
            ),
            (
                "requested_3bhk_units",
                "3BHK",
            ),
        )

        for field_name, bhk in mappings:

            units = getattr(
                facts,
                field_name,
                None,
            )

            if units is None:
                continue

            # Carpet area may be supplied through the
            # existing values dictionary.
            carpet_area = (
                self._fact_value(
                    facts,
                    f"{bhk.lower()}_carpet_area",
                )
                or self._fact_value(
                    facts,
                    f"requested_{bhk.lower()}_carpet_area",
                )
            )

            if carpet_area is None:
                continue

            result.append(
                {
                    "bhk": bhk,
                    "units": units,
                    "carpet_area": carpet_area,
                }
            )

        return result

    # ---------------------------------------------------------
    # FACT LOOKUP
    # ---------------------------------------------------------

    def _fact_value(
        self,
        facts,
        key: str,
    ):

        values = getattr(
            facts,
            "values",
            None,
        )

        if isinstance(
            values,
            dict,
        ):
            return values.get(key)

        return None

    # ---------------------------------------------------------
    # CONGESTED AREA
    # ---------------------------------------------------------

    def _is_congested(
        self,
        facts,
    ) -> bool:

        value = self._fact_value(
            facts,
            "congested_area",
        )

        if value is None:
            value = self._fact_value(
                facts,
                "is_congested_area",
            )

        if value is None:
            value = self._fact_value(
                facts,
                "congested",
            )

        if isinstance(
            value,
            str,
        ):
            return value.lower() in {
                "true",
                "yes",
                "1",
                "congested",
            }

        return bool(value)

    # ---------------------------------------------------------
    # FIND TABLE ROW
    # ---------------------------------------------------------

    def _find_residential_rule(
        self,
        table,
        carpet_area: float,
    ):

        rows = (
            getattr(
                table,
                "rows",
                []
            )
            or []
        )

        # Table 8-B layout:
        #
        # row[2] = occupancy
        # row[3] = size/condition
        # row[4] = congested car
        # row[7] = congested scooter
        # row[10] = non-congested car
        # row[13] = non-congested scooter
        # row[16] = remarks
        #
        # The first 3 rows are table headers.

        for row in rows:

            if len(row) < 14:
                continue

            occupancy = str(
                row[2]
                if len(row) > 2
                else ""
            ).lower()

            condition = str(
                row[3]
                if len(row) > 3
                else ""
            )

            combined = (
                occupancy
                + " "
                + condition.lower()
            )

            # We only want:
            # Residential
            # i) Multi-Family residential
            #
            # Do not accidentally select hotels/restaurants.
            if (
                "residential" not in combined
                and "tenement" not in combined
            ):
                continue

            if (
                "lodging" in combined
                or "hotel" in combined
                or "restaurant" in combined
            ):
                continue

            parsed = self._parse_condition(
                condition
            )

            if parsed is None:
                continue

            if not (
                parsed["min_area"]
                <= carpet_area
            ):
                continue

            max_area = parsed[
                "max_area"
            ]

            if (
                max_area is not None
                and carpet_area >= max_area
            ):
                continue

            congested_car = self._number(
                row[4]
            )

            congested_scooter = self._number(
                row[7]
            )

            non_congested_car = self._number(
                row[10]
            )

            non_congested_scooter = self._number(
                row[13]
            )

            if (
                congested_car is None
                or congested_scooter is None
                or non_congested_car is None
                or non_congested_scooter is None
            ):
                continue

            return {
                "min_area": parsed["min_area"],
                "max_area": parsed["max_area"],
                "divisor": parsed["divisor"],
                "congested_car": congested_car,
                "congested_scooter": congested_scooter,
                "non_congested_car": non_congested_car,
                "non_congested_scooter": non_congested_scooter,
                "rule_text": condition,
            }

        return None

    # ---------------------------------------------------------
    # PARSE CARPET-AREA CONDITION
    # ---------------------------------------------------------

    def _parse_condition(
        self,
        text: str,
    ):

        text = (
            text
            .replace("\n", " ")
            .strip()
            .lower()
        )

        # -----------------------------------------------------
        # 150 sq.m. and above
        # -----------------------------------------------------

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*sq\.?\s*m.*above",
            text,
        )

        if match:

            return {
                "min_area": float(
                    match.group(1)
                ),
                "max_area": None,
                "divisor": 1.0,
            }

        # -----------------------------------------------------
        # 80 sq.m. but less than 150 sq.m.
        # -----------------------------------------------------

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*sq\.?\s*m.*"
            r"(?:less than|below)\s*"
            r"(\d+(?:\.\d+)?)",
            text,
        )

        if match:

            return {
                "min_area": float(
                    match.group(1)
                ),
                "max_area": float(
                    match.group(2)
                ),
                "divisor": 1.0,
            }

        # -----------------------------------------------------
        # Every two tenements
        # -----------------------------------------------------

        divisor = 1.0

        if "every two tenements" in text:
            divisor = 2.0

        # -----------------------------------------------------
        # 40 to 80 sq.m.
        # -----------------------------------------------------

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*sq\.?\s*m.*"
            r"(?:less than|below)\s*"
            r"(\d+(?:\.\d+)?)",
            text,
        )

        if match:

            low = float(
                match.group(1)
            )

            high = float(
                match.group(2)
            )

            return {
                "min_area": low,
                "max_area": high,
                "divisor": divisor,
            }

        # -----------------------------------------------------
        # Less than 40 but more than 30
        # -----------------------------------------------------

        match = re.search(
            r"less than\s*(\d+(?:\.\d+)?)"
            r".*more than\s*(\d+(?:\.\d+)?)",
            text,
        )

        if match:

            high = float(
                match.group(1)
            )

            low = float(
                match.group(2)
            )

            return {
                "min_area": low,
                "max_area": high,
                "divisor": 2.0,
            }

        # -----------------------------------------------------
        # Less than 30
        # -----------------------------------------------------

        match = re.search(
            r"less than\s*(\d+(?:\.\d+)?)",
            text,
        )

        if match:

            high = float(
                match.group(1)
            )

            return {
                "min_area": 0.0,
                "max_area": high,
                "divisor": 2.0,
            }

        return None

    # ---------------------------------------------------------
    # NUMBER
    # ---------------------------------------------------------

    @staticmethod
    def _number(
        value,
    ):

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return None

        if isinstance(
            value,
            (int, float),
        ):
            return float(value)

        text = str(
            value
        ).strip()

        # Handle values such as:
        # "(1) 1"
        # "(1) 2"
        # "2"
        match = re.search(
            r"(\d+(?:\.\d+)?)",
            text,
        )

        if not match:
            return None

        return float(
            match.group(1)
        )
