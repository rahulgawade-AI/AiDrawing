"""
Generic regulatory data extraction.

This layer identifies regulatory concepts present in extracted
UDCPR source data.

It does NOT determine which rule applies to a particular project.
"""

from __future__ import annotations

import re
from typing import Any

from townplanning.modules.regulations.ingestion.table import (
    ExtractedTable,
)

from townplanning.modules.regulations.extraction.regulatory_data import (
    RegulatoryTableData,
    RegulatoryValue,
)


class RegulatoryDataExtractor:
    """
    Generic source-data extractor.

    Designed to work across:
        - FSI
        - building height
        - floors
        - setbacks
        - margins
        - parking
        - fire requirements
        - open space
        - amenity
        - road/access requirements
        - plot requirements
        - and future regulatory categories
    """

    FIELD_PATTERNS: dict[str, tuple[str, ...]] = {
        "fsi": (
            r"\bfsi\b",
            r"floor\s*space\s*index",
        ),
        "basic_fsi": (
            r"basic\s*fsi",
        ),
        "premium_fsi": (
            r"premium\s*fsi",
        ),
        "tdr": (
            r"\btdr\b",
            r"transferable\s+development",
        ),
        "maximum_fsi": (
            r"maximum\s*fsi",
            r"max(?:imum)?\s+building\s+potential",
            r"maximum\s+building\s+potential",
        ),
        "building_height": (
            r"building\s+height",
            r"maximum\s+height",
            r"height\s+of\s+building",
        ),
        "floor_count": (
            r"number\s+of\s+floors",
            r"no\.?\s+of\s+floors",
            r"permissible\s+floors",
            r"number\s+of\s+storeys",
            r"storeys",
            r"stories",
        ),
        "floor_height": (
            r"floor\s+height",
            r"storey\s+height",
            r"floor\s+to\s+floor",
        ),
        "setback": (
            r"setback",
            r"set\s*back",
        ),
        "front_setback": (
            r"front\s+(?:setback|margin|open\s+space)",
        ),
        "side_setback": (
            r"side\s+(?:setback|margin|open\s+space)",
        ),
        "rear_setback": (
            r"rear\s+(?:setback|margin|open\s+space)",
        ),
        "margin": (
            r"\bmargin\b",
            r"marginal\s+open\s+space",
        ),
        "parking": (
            r"\bparking\b",
            r"parking\s+requirement",
        ),
        "fire": (
            r"\bfire\b",
            r"fire\s+requirement",
            r"fire\s+protection",
        ),
        "open_space": (
            r"open\s+space",
            r"recreational\s+open\s+space",
        ),
        "amenity": (
            r"\bamenit(?:y|ies)\b",
        ),
        "road_width": (
            r"road\s+width",
            r"width\s+of\s+road",
        ),
        "plot_area": (
            r"plot\s+area",
            r"area\s+of\s+plot",
        ),
        "plot_width": (
            r"plot\s+width",
            r"width\s+of\s+plot",
        ),
        "plot_depth": (
            r"plot\s+depth",
            r"depth\s+of\s+plot",
        ),
        "unit_area": (
            r"unit\s+area",
            r"carpet\s+area",
            r"built[-\s]?up\s+area\s+of\s+unit",
        ),
        "building_use": (
            r"building\s+use",
            r"use\s+of\s+building",
            r"occupancy",
        ),
        "authority": (
            r"municipal\s+corporation",
            r"municipality",
            r"development\s+authority",
            r"competent\s+authority",
            r"planning\s+authority",
            r"authority",
        ),
        "zone": (
            r"\bzone\b",
            r"land\s+use",
            r"zoning",
        ),
    }

    UNIT_PATTERN = re.compile(
        r"""
        (?P<value>
            [-+]?
            (?:
                \d+(?:\.\d*)?
                |
                \.\d+
            )
        )
        \s*
        (?P<unit>
            m2|m²|sq\.?\s*m|sqm|
            m|meter(?:s)?|metre(?:s)?|
            %|percent|
            floor(?:s)?|
            storey|storeys|
            nos?\.?|number(?:s)?
        )?
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def extract_table(
        self,
        table: ExtractedTable,
        regulation_number: str | None = None,
    ) -> RegulatoryTableData:

        headers = [
            self._normalize_text(value)
            for value in (
                table.headers or []
            )
        ]

        header_rows = [
            [
                self._normalize_text(value)
                for value in row
            ]
            for row in (
                table.header_rows or []
            )
        ]

        rows = [
            [
                self._normalize_text(value)
                for value in row
            ]
            for row in (
                table.rows or []
            )
        ]

        searchable_header = " | ".join(
            headers
        )

        searchable_all = " | ".join(
            headers
        )

        for row in header_rows:
            searchable_all += (
                " | "
                + " | ".join(row)
            )

        for row in rows:
            searchable_all += (
                " | "
                + " | ".join(row)
            )

        identified_fields = (
            self.identify_fields(
                searchable_all
            )
        )

        identified_conditions = (
            self.identify_conditions(
                searchable_all
            )
        )

        values = self.extract_values(
            table=table,
            regulation_number=(
                regulation_number
            ),
            identified_fields=(
                identified_fields
            ),
        )

        metadata = {
            "extractor": (
                "generic_regulatory_data_extractor"
            ),
            "semantic_fields_detected": (
                bool(identified_fields)
            ),
            "condition_fields_detected": (
                bool(identified_conditions)
            ),
            "value_count": len(values),
            "source_preserved": True,
            "project_specific_evaluation": False,
        }

        return RegulatoryTableData(
            table_id=table.id,
            title=table.title,
            page=table.page,
            headers=headers,
            header_rows=header_rows,
            rows=rows,
            identified_fields=(
                identified_fields
            ),
            identified_conditions=(
                identified_conditions
            ),
            values=values,
            metadata=metadata,
        )

    # ============================================================
    # FIELD DETECTION
    # ============================================================

    def identify_fields(
        self,
        text: str,
    ) -> list[str]:

        normalized = self._normalize_text(
            text
        )

        found: list[str] = []

        for field_name, patterns in (
            self.FIELD_PATTERNS.items()
        ):
            if any(
                re.search(
                    pattern,
                    normalized,
                    flags=re.IGNORECASE,
                )
                for pattern in patterns
            ):
                found.append(field_name)

        return found

    def identify_conditions(
        self,
        text: str,
    ) -> list[str]:

        normalized = self._normalize_text(
            text
        )

        condition_patterns = {
            "road_width": (
                r"road\s+width",
                r"width\s+of\s+road",
            ),
            "plot_area": (
                r"plot\s+area",
            ),
            "plot_width": (
                r"plot\s+width",
            ),
            "plot_depth": (
                r"plot\s+depth",
            ),
            "building_use": (
                r"building\s+use",
                r"occupancy",
                r"residential",
                r"commercial",
                r"industrial",
            ),
            "building_type": (
                r"building\s+type",
                r"type\s+of\s+building",
            ),
            "authority": (
                r"authority",
                r"municipal\s+corporation",
                r"municipality",
                r"development\s+authority",
            ),
            "zone": (
                r"\bzone\b",
                r"land\s+use",
            ),
            "height": (
                r"height",
            ),
            "floors": (
                r"floors",
                r"storeys",
                r"stories",
            ),
        }

        found: list[str] = []

        for field_name, patterns in (
            condition_patterns.items()
        ):
            if any(
                re.search(
                    pattern,
                    normalized,
                    flags=re.IGNORECASE,
                )
                for pattern in patterns
            ):
                found.append(field_name)

        return found

    # ============================================================
    # VALUE EXTRACTION
    # ============================================================

    def extract_values(
        self,
        table: ExtractedTable,
        regulation_number: str | None,
        identified_fields: list[str],
    ) -> list[RegulatoryValue]:

        values: list[RegulatoryValue] = []

        # --------------------------------------------------------
        # We only extract numeric values from cells that have
        # contextual evidence in their row/header.
        #
        # We do NOT assign arbitrary numbers to regulatory fields.
        # --------------------------------------------------------

        headers = table.headers or []

        for row_index, row in enumerate(
            table.rows or []
        ):

            for column_index, cell in enumerate(
                row
            ):

                text = self._normalize_text(
                    cell
                )

                if not text:
                    continue

                context_parts = []

                if column_index < len(headers):
                    context_parts.append(
                        headers[column_index]
                    )

                context_parts.extend(
                    identified_fields
                )

                context = " ".join(
                    context_parts
                )

                candidate_fields = (
                    self.identify_fields(
                        context
                    )
                )

                if not candidate_fields:
                    continue

                numbers = self._extract_numbers(
                    text
                )

                if not numbers:
                    continue

                for field_name in candidate_fields:
                    for number, unit in numbers:

                        values.append(
                            RegulatoryValue(
                                field=field_name,
                                value=number,
                                unit=unit,
                                source_page=(
                                    table.page
                                ),
                                source_table_id=(
                                    table.id
                                ),
                                source_regulation=(
                                    regulation_number
                                ),
                                source_text=text,
                                confidence=0.80,
                                metadata={
                                    "row_index": (
                                        row_index
                                    ),
                                    "column_index": (
                                        column_index
                                    ),
                                    "extraction": (
                                        "contextual_numeric"
                                    ),
                                },
                            )
                        )

        return values

    # ============================================================
    # NUMBER PARSING
    # ============================================================

    def _extract_numbers(
        self,
        text: str,
    ) -> list[tuple[float, str | None]]:

        output: list[
            tuple[float, str | None]
        ] = []

        for match in self.UNIT_PATTERN.finditer(
            text
        ):
            try:
                value = float(
                    match.group("value")
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            unit = match.group(
                "unit"
            )

            if unit:
                unit = self._normalize_text(
                    unit
                )

            output.append(
                (
                    value,
                    unit,
                )
            )

        return output

    # ============================================================
    # TEXT NORMALIZATION
    # ============================================================

    @staticmethod
    def _normalize_text(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        text = str(value)

        text = text.replace(
            "\r\n",
            "\n",
        )
        text = text.replace(
            "\r",
            "\n",
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()
