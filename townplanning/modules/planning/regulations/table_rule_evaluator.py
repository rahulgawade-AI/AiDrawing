from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TableMatchResult:
    matched: bool
    result: dict[str, Any]
    table_id: str | None = None
    table_title: str | None = None
    matched_row: dict[str, Any] | None = None
    matched_dimensions: dict[str, Any] | None = None
    reason: str | None = None


class GenericTableRuleEvaluator:
    """
    Generic evaluator for structured UDCPR tables.

    This class does not know anything about:
      - FSI
      - parking
      - setbacks
      - height
      - fire
      - any specific regulation

    It resolves a table row using PlanningFacts and returns
    normalized regulatory values.

    Regulatory interpretation remains deterministic.
    """

    FACT_ALIASES = {
        "road width": "road_width",
        "road_width": "road_width",
        "road width in meters": "road_width",

        "plot area": "plot_area",
        "plot_area": "plot_area",
        "plot area in sq.m.": "plot_area",

        "building height": "building_height",
        "height": "building_height",

        "floor height": "floor_height",
        "number of floors": "number_of_floors",
        "storeys": "number_of_floors",

        "building type": "building_type",
        "building use": "building_use",
        "occupancy": "occupancy",
        "occupancy type": "occupancy_type",

        "authority": "planning_authority",
        "planning authority": "planning_authority",
        "development authority": "development_authority",
        "municipal corporation": "municipal_corporation",

        "zone": "zone",
        "zone type": "zone_type",
        "land use zone": "land_use_zone",
    }

    OUTPUT_ALIASES = {
        "basic fsi": "basic_fsi",
        "basic permissible fsi": "basic_fsi",
        "basic_fsi": "basic_fsi",

        "premium fsi": "premium_fsi",
        "fsi on payment of premium": "premium_fsi",
        "additional fsi": "premium_fsi",

        "tdr": "tdr_fsi",
        "tdr loading": "tdr_fsi",
        "maximum permissible tdr loading": "tdr_fsi",

        "maximum building potential": "maximum_fsi",
        "maximum building potential on plot": "maximum_fsi",
        "maximum permissible fsi": "maximum_fsi",
        "maximum total fsi": "maximum_fsi",
        "maximum_fsi": "maximum_fsi",

        "front margin": "front_setback",
        "front margin in m.": "front_setback",
        "front setback": "front_setback",

        "side margin": "side_setback",
        "side margin in m.": "side_setback",
        "side setback": "side_setback",

        "rear margin": "rear_setback",
        "rear setback": "rear_setback",

        "minimum height": "minimum_height_m",
        "maximum height": "maximum_height_m",

        "parking": "parking_requirement",
    }

    def __init__(self, table_repository=None):
        self.table_repository = table_repository

    # ============================================================
    # PUBLIC API
    # ============================================================

    def evaluate(
        self,
        *,
        table: Any,
        facts: Any,
    ) -> TableMatchResult:

        headers = list(getattr(table, "headers", None) or [])
        rows = list(getattr(table, "rows", None) or [])

        if not headers:
            return TableMatchResult(
                matched=False,
                result={},
                table_id=self._table_id(table),
                table_title=self._table_title(table),
                reason="Table has no structured headers.",
            )

        if not rows:
            return TableMatchResult(
                matched=False,
                result={},
                table_id=self._table_id(table),
                table_title=self._table_title(table),
                reason="Table has no structured rows.",
            )

        normalized_headers = self._normalize_headers(headers)

        for raw_row in rows:
            row = self._normalize_row(
                normalized_headers,
                raw_row,
            )

            if not row:
                continue

            match = self._match_row(
                row=row,
                facts=facts,
            )

            if not match["matched"]:
                continue

            result = self._extract_outputs(row)

            return TableMatchResult(
                matched=True,
                result=result,
                table_id=self._table_id(table),
                table_title=self._table_title(table),
                matched_row=row,
                matched_dimensions=match["dimensions"],
                reason="Structured table row matched deterministically.",
            )

        return TableMatchResult(
            matched=False,
            result={},
            table_id=self._table_id(table),
            table_title=self._table_title(table),
            reason="No structured table row matched the available PlanningFacts.",
        )

    # ============================================================
    # HEADER NORMALIZATION
    # ============================================================

    def _normalize_headers(
        self,
        headers: list[Any],
    ) -> list[str]:

        result = []

        for header in headers:
            text = self._clean_text(header)

            if not text:
                result.append("")
                continue

            result.append(
                re.sub(
                    r"\s+",
                    " ",
                    text,
                ).strip().lower()
            )

        return result

    # ============================================================
    # ROW NORMALIZATION
    # ============================================================

    def _normalize_row(
        self,
        headers: list[str],
        raw_row: Any,
    ) -> dict[str, Any]:

        if isinstance(raw_row, dict):
            return {
                self._clean_text(key).lower(): value
                for key, value in raw_row.items()
                if self._clean_text(key)
            }

        if not isinstance(raw_row, (list, tuple)):
            return {}

        row = {}

        for index, value in enumerate(raw_row):
            if index >= len(headers):
                break

            header = headers[index]

            if not header:
                continue

            if value is None:
                continue

            text = self._clean_text(value)

            if not text:
                continue

            row[header] = text

        return row

    # ============================================================
    # ROW MATCHING
    # ============================================================

    def _match_row(
        self,
        *,
        row: dict[str, Any],
        facts: Any,
    ) -> dict[str, Any]:

        dimensions = {}

        for header, value in row.items():

            fact_name = self._fact_for_header(header)

            if fact_name is None:
                continue

            fact_value = getattr(
                facts,
                fact_name,
                None,
            )

            if fact_value is None:
                continue

            dimensions[fact_name] = fact_value

            if not self._value_matches(
                header=header,
                table_value=value,
                fact_value=fact_value,
            ):
                return {
                    "matched": False,
                    "dimensions": dimensions,
                }

        # A row that has no recognizable dimension is not
        # allowed to become an arbitrary match.
        if not dimensions:
            return {
                "matched": False,
                "dimensions": {},
            }

        return {
            "matched": True,
            "dimensions": dimensions,
        }

    # ============================================================
    # FACT IDENTIFICATION
    # ============================================================

    def _fact_for_header(
        self,
        header: str,
    ) -> str | None:

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            header.lower(),
        ).strip()

        if normalized in self.FACT_ALIASES:
            return self.FACT_ALIASES[normalized]

        for key, fact in self.FACT_ALIASES.items():
            if key in normalized:
                return fact

        return None

    # ============================================================
    # VALUE MATCHING
    # ============================================================

    def _value_matches(
        self,
        *,
        header: str,
        table_value: Any,
        fact_value: Any,
    ) -> bool:

        text = self._clean_text(table_value).lower()

        if not text:
            return False

        # Numeric range matching.
        if isinstance(
            fact_value,
            (int, float),
        ):
            return self._numeric_matches(
                text,
                float(fact_value),
            )

        # Textual matching.
        fact_text = self._clean_text(
            fact_value
        ).lower()

        if text == fact_text:
            return True

        if fact_text in text:
            return True

        if text in fact_text:
            return True

        return False

    def _numeric_matches(
        self,
        text: str,
        value: float,
    ) -> bool:

        text = text.replace(
            ",",
            "",
        )

        numbers = [
            float(x)
            for x in re.findall(
                r"\d+(?:\.\d+)?",
                text,
            )
        ]

        if not numbers:
            return False

        lowered = text.lower()

        # Below X
        if "below" in lowered:
            return value < numbers[-1]

        # X and above
        if "and above" in lowered:
            return value >= numbers[0]

        # Above X
        if lowered.startswith("above"):
            return value > numbers[0]

        # Up to X
        if "up to" in lowered:
            return value <= numbers[-1]

        # X to Y
        if len(numbers) >= 2:
            low = numbers[0]
            high = numbers[1]

            return low <= value <= high

        # Exact numeric value.
        return abs(value - numbers[0]) < 1e-9

    # ============================================================
    # OUTPUT EXTRACTION
    # ============================================================

    def _extract_outputs(
        self,
        row: dict[str, Any],
    ) -> dict[str, Any]:

        result = {}

        for header, value in row.items():

            output_name = self._output_for_header(
                header
            )

            if output_name is None:
                continue

            number = self._number(value)

            if number is None:
                continue

            result[output_name] = number

        return result

    def _output_for_header(
        self,
        header: str,
    ) -> str | None:

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            header.lower(),
        ).strip()

        if normalized in self.OUTPUT_ALIASES:
            return self.OUTPUT_ALIASES[
                normalized
            ]

        for key, output in self.OUTPUT_ALIASES.items():
            if key in normalized:
                return output

        return None

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _number(value: Any) -> float | None:

        if isinstance(
            value,
            (int, float),
        ):
            return float(value)

        text = str(value).strip()

        if not text:
            return None

        match = re.search(
            r"\d+(?:\.\d+)?",
            text.replace(",", ""),
        )

        if not match:
            return None

        try:
            return float(match.group())
        except ValueError:
            return None

    @staticmethod
    def _clean_text(value: Any) -> str:

        if value is None:
            return ""

        if isinstance(value, (list, tuple)):
            return " ".join(
                str(x)
                for x in value
                if x is not None
            ).strip()

        return str(value).strip()

    @staticmethod
    def _table_id(table: Any) -> str | None:
        value = getattr(table, "id", None)
        return str(value) if value is not None else None

    @staticmethod
    def _table_title(table: Any) -> str | None:
        value = getattr(table, "title", None)
        return str(value) if value is not None else None
