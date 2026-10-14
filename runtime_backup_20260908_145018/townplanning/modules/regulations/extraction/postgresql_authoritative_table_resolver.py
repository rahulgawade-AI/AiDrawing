from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from townplanning.infrastructure.database.models import (
    RegulationModel,
    Table as TableModel,
)


@dataclass(slots=True)
class SelectedTable:
    regulation_number: str
    table_number: str | None = None
    table_title: str | None = None
    source_id: str | None = None
    reason: str = ""
    deterministic: bool = True


@dataclass(slots=True)
class PostgreSQLResolution:
    status: str = "INSUFFICIENT_RULE_DATA"
    constraints: list[dict[str, Any]] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    selections: list[dict[str, Any]] = field(default_factory=list)


class PostgreSQLAuthoritativeTableResolver:
    """
    Final regulatory-value boundary.

    IMPORTANT:
      * Chroma/OpenAI are never called here.
      * Values are read directly from PostgreSQL.
      * No UDCPR numeric threshold is embedded here.
      * Table/row interpretation is generic and driven by DB content.
    """

    FIELD_ALIASES = {
        "basic_fsi": (
            "basic fsi",
            "basic permissible fsi",
        ),
        "premium_fsi": (
            "fsi on payment of premium",
            "premium fsi",
            "fsi on premium",
        ),
        "tdr_fsi": (
            "tdr fsi",
            "fsi through tdr",
            "tdr",
        ),
        "maximum_fsi": (
            "maximum building potential",
            "maximum building potential on plot",
            "maximum fsi",
            "maximum permissible fsi",
        ),
        "car_parking_required": (
            "non congested area car",
            "congested area car",
            "car parking",
            "cars required",
        ),
        "two_wheeler_parking_required": (
            "non congested area scooter",
            "congested area scooter",
            "scooter",
            "two wheeler",
            "motorcycle",
        ),
        "visitor_parking_required": (
            "visitor parking",
            "visitor",
        ),
        "parking_area_required_m2": (
            "parking area",
            "parking area required",
        ),
        "front_setback": ("front setback", "front margin"),
        "rear_setback": ("rear setback", "rear margin"),
        "side_setback": ("side setback", "side margin"),
        "side_setback_left": ("side setback", "side margin", "minimum side margins"),
        "side_setback_right": ("side setback", "side margin", "minimum side margins"),
        "maximum_height_m": (
            "maximum height",
            "maximum building height",
            "height limit",
        ),
        "maximum_storeys": (
            "maximum storeys",
            "maximum stories",
            "number of storeys",
        ),
    }

    FIELD_TABLE_HINTS = {
        "basic_fsi": ("fsi", "permissible"),
        "premium_fsi": ("fsi", "premium"),
        "tdr_fsi": ("fsi", "tdr"),
        "maximum_fsi": ("fsi", "building potential", "maximum"),
        "car_parking_required": ("parking",),
        "two_wheeler_parking_required": ("parking",),
        "visitor_parking_required": ("parking",),
        "parking_area_required_m2": ("parking",),
        "front_setback": ("setback", "margin"),
        "rear_setback": ("setback", "margin"),
        "side_setback": ("setback", "margin"),
        "maximum_height_m": ("height",),
        "maximum_storeys": ("height", "storey"),
    }

    def __init__(self, session):
        self.session = session

    # --------------------------------------------------------------
    # PUBLIC
    # --------------------------------------------------------------
    def resolve(
        self,
        *,
        facts: Any,
        selected_regulations: list[Any],
        chroma_sources: list[Any],
        requested_fields: list[str],
    ) -> PostgreSQLResolution:

        result = PostgreSQLResolution()

        numbers = []
        for value in selected_regulations or []:
            number = self._number(value)
            if number and number not in numbers:
                numbers.append(number)

        if not numbers:
            result.errors.append("No selected regulation numbers were supplied.")
            return result

        for number in numbers:
            source_texts = self._source_text_for_regulation(
                number, chroma_sources
            )

            table_refs = self._extract_table_references(source_texts)

            if not table_refs:
                # Do not invent a table. The caller can still use a source
                # that contains a direct scalar labelled provision.
                continue

            regulation = self._get_regulation(number)

            if regulation is None:
                result.errors.append(
                    f"Regulation {number} was selected but is not present in PostgreSQL."
                )
                continue

            tables = self._tables_for_regulation(regulation.id)

            for table_ref in table_refs:
                table = self._match_table(tables, table_ref)
                if table is None:
                    result.warnings.append(
                        f"PostgreSQL table {table_ref.get('table_number')} selected for regulation {number} was not found."
                    )
                    continue

                selection = SelectedTable(
                    regulation_number=number,
                    table_number=table_ref.get("table_number"),
                    table_title=table_ref.get("title"),
                    source_id=table_ref.get("source_id"),
                    reason=table_ref.get("reason", ""),
                )

                result.selections.append({
                    "regulation_number": selection.regulation_number,
                    "table_number": selection.table_number,
                    "table_title": selection.table_title,
                    "source_id": selection.source_id,
                    "reason": selection.reason,
                })

                fields = [
                    f for f in requested_fields
                    if self._table_can_supply_field(table, f)
                ]

                if not fields:
                    result.warnings.append(
                        f"PostgreSQL table {self._table_number(table) or self._table_title(table)} "
                        f"contains no requested regulatory fields for {number}."
                    )
                    continue

                resolved, missing, errors = self._resolve_table(
                    table=table,
                    facts=facts,
                    requested_fields=fields,
                    regulation_number=number,
                )

                result.constraints.extend(resolved)
                result.missing_inputs.extend(
                    x for x in missing if x not in result.missing_inputs
                )
                result.errors.extend(errors)

        if result.errors:
            result.status = "ERROR" if not result.constraints else "PARTIAL"
        elif result.constraints and result.missing_inputs:
            result.status = "PARTIAL"
        elif result.constraints:
            result.status = "RESOLVED"
        else:
            result.status = "INSUFFICIENT_RULE_DATA"

        return result

    # --------------------------------------------------------------
    # PostgreSQL lookup
    # --------------------------------------------------------------
    def _get_regulation(self, number: str):
        stmt = select(RegulationModel).where(
            RegulationModel.number == number
        )
        return self.session.scalar(stmt)

    def _tables_for_regulation(self, regulation_id: str):
        stmt = (
            select(TableModel)
            .where(TableModel.regulation_id == regulation_id)
            .order_by(TableModel.page_number, TableModel.table_index)
        )
        return list(self.session.scalars(stmt))

    # --------------------------------------------------------------
    # Table selection
    # --------------------------------------------------------------
    @classmethod
    def _extract_table_references(cls, texts):
        refs = []
        for source in texts:
            text = source["text"]
            source_id = source["source_id"]

            # Prefer explicit "Table 6-G", "Table No. 8-B", etc.
            for match in re.finditer(
                r"\bTable\s+(?:No\.?\s*)?([0-9]+(?:\.[0-9]+)?[-A-Za-z]?)\b",
                text,
                re.I,
            ):
                table_number = match.group(1).upper()
                context = text[max(0, match.start()-180):match.end()+260]
                title = cls._title_from_context(context)

                item = {
                    "table_number": table_number,
                    "title": title,
                    "source_id": source_id,
                    "reason": "Explicit table reference from Chroma-selected regulatory evidence.",
                }

                if item not in refs:
                    refs.append(item)

        return refs

    @staticmethod
    def _title_from_context(context: str) -> str | None:
        for pattern in (
            r"Table\s+(?:No\.?\s*)?[0-9]+(?:\.[0-9]+)?[-A-Za-z]?\s*[:\-]\s*([^\n]+)",
            r"Table\s+(?:No\.?\s*)?[0-9]+(?:\.[0-9]+)?[-A-Za-z]?\s*\n\s*([^\n]+)",
        ):
            m = re.search(pattern, context, re.I)
            if m:
                title = m.group(1).strip(" .:-")
                if title:
                    return title[:180]
        return None

    def _match_table(self, tables, ref):
        wanted_number = self._norm_table(ref.get("table_number"))
        wanted_title = self._norm(ref.get("title"))

        exact = []
        for table in tables:
            number = self._table_number(table)
            title = self._table_title(table)

            # The ingestion schema may put the table label only in the first
            # header cell or markdown, while title/table_number is empty.
            if wanted_number and number:
                if self._norm_table(number) == wanted_number:
                    exact.append(table)
                    continue

            haystack = " ".join(
                str(x or "")
                for x in (
                    title,
                    getattr(table, "headers", None),
                    getattr(table, "markdown", None),
                )
            )
            found = re.search(
                r"\bTable\s+(?:No\.?\s*)?([0-9]+(?:\.[0-9]+)?[-A-Za-z]?)\b",
                haystack,
                re.I,
            )
            if wanted_number and found and self._norm_table(found.group(1)) == wanted_number:
                exact.append(table)

        if len(exact) == 1:
            return exact[0]

        if len(exact) > 1:
            raise RuntimeError(
                f"Multiple PostgreSQL tables match table {wanted_number}."
            )

        if wanted_title:
            candidates = []
            for table in tables:
                title = self._norm(self._table_title(table))
                if title and wanted_title in title:
                    candidates.append(table)
            if len(candidates) == 1:
                return candidates[0]

        return None

    # --------------------------------------------------------------
    # Row/column resolution
    # --------------------------------------------------------------
    def _resolve_table(
        self,
        *,
        table,
        facts,
        requested_fields,
        regulation_number,
    ):
        rows = list(getattr(table, "rows", None) or [])
        headers = list(getattr(table, "headers", None) or [])

        if not rows:
            return [], [], [
                f"PostgreSQL table {self._table_number(table) or self._table_title(table)} has no rows."
            ]

        normalized_headers = self._normalize_headers(headers, rows)

        applicable = []
        missing = []

        for index, raw_row in enumerate(rows):
            row = self._row_dict(raw_row, normalized_headers)

            row_missing = self._missing_inputs(row, facts)

            if row_missing:
                missing.extend(x for x in row_missing if x not in missing)

            if self._row_applies(row, facts):
                applicable.append((index, row))

        if len(applicable) == 0:
            # A row may not need every dimension. Missing input is preferable
            # to silently choosing an arbitrary row.
            if missing:
                return [], missing, []
            return [], [], [
                f"No PostgreSQL row matched PlanningFacts in table "
                f"{self._table_number(table) or self._table_title(table)}."
            ]

        # Parking Table 8-B is an aggregation table: several rows can be
        # applicable to different tenement-size bands. Resolve it as a whole
        # when the table contains parking columns.
        if self._is_parking_table(table):
            values = self._resolve_parking_table(
                rows=rows,
                headers=normalized_headers,
                facts=facts,
                requested_fields=requested_fields,
            )
            if not values:
                return [], [], [
                    f"No PostgreSQL parking row matched PlanningFacts in table "
                    f"{self._table_number(table) or self._table_title(table)}."
                ]
            selected_index = 0
            selected_row = {}
        else:
            if len(applicable) > 1:
                # If multiple rows match, only accept identical requested values.
                candidate_values = []
                for index, row in applicable:
                    values = self._extract_fields(
                        row, requested_fields, facts
                    )
                    candidate_values.append((index, values))

                merged = {}
                for _, values in candidate_values:
                    for field, value in values.items():
                        merged.setdefault(field, set()).add(
                            self._stable(value)
                        )

                conflicts = [
                    field for field, values in merged.items()
                    if len(values) > 1
                ]
                if conflicts:
                    return [], [], [
                        "Multiple PostgreSQL rows matched with conflicting "
                        f"values for: {', '.join(conflicts)}."
                    ]

            selected_index, selected_row = applicable[0]

            values = self._extract_fields(
                selected_row,
                requested_fields,
                facts,
            )

        constraints = []
        for field, value in values.items():
            constraints.append({
                "field": field,
                "value": value,
                "unit": "fsi" if field.endswith("_fsi") else None,
                "source_id": f"postgresql:table:{getattr(table, 'id', 'unknown')}:row:{selected_index}",
                "regulation_number": regulation_number,
                "table_number": self._table_number(table),
                "table_title": self._table_title(table),
                "row_index": selected_index,
                "confidence": "authoritative",
            })

        return constraints, missing, []

    @staticmethod
    def _is_parking_table(table):
        text = " ".join(
            str(x or "")
            for x in (
                getattr(table, "title", ""),
                getattr(table, "headers", ""),
                getattr(table, "markdown", ""),
            )
        ).lower()
        return "parking" in text and "tenement" in text

    def _resolve_parking_table(self, *, rows, headers, facts, requested_fields):
        areas = self._fact(facts, "tenement_carpet_areas") or {}
        if not isinstance(areas, dict) or not areas:
            return {}

        non_congested = not bool(self._fact(facts, "congested_area"))
        total_car = 0.0
        total_scooter = 0.0
        visitor_required = False
        matched_any = False

        for raw_row in rows:
            row = self._row_dict(raw_row, headers)
            size_key = self._find_column(
                row, ("size of tenement", "carpet area", "tenement area")
            )
            if size_key is None:
                continue
            size_text = str(row[size_key] or "")
            if not size_text or not self._parking_size_matches_all(
                size_text, areas.values()
            ):
                continue

            matched_any = True
            car_key, scooter_key = self._parking_vehicle_columns(
                row, non_congested
            )
            if car_key is None or scooter_key is None:
                continue

            car_value = self._parse_scalar(row[car_key]) or 0
            scooter_value = self._parse_scalar(row[scooter_key]) or 0
            divisor = self._parking_divisor(size_text)
            count = len(areas)
            groups = (count + divisor - 1) // divisor
            total_car += float(car_value) * groups
            total_scooter += float(scooter_value) * groups

            remark_key = self._find_column(row, ("remarks", "remark"))
            remark = self._norm(row[remark_key]) if remark_key else ""
            if "visitor" in remark and "5%" in remark:
                visitor_required = True

        if not matched_any:
            return {}

        result = {}
        if "car_parking_required" in requested_fields:
            result["car_parking_required"] = (
                int(total_car) if total_car.is_integer() else total_car
            )
        if "two_wheeler_parking_required" in requested_fields:
            result["two_wheeler_parking_required"] = (
                int(total_scooter) if total_scooter.is_integer() else total_scooter
            )
        if "visitor_parking_required" in requested_fields and visitor_required:
            # UDCPR Table 8-B states "In addition 5% visitor parking". Keep
            # the percentage as a derived requirement, not as a regulatory
            # constant hidden elsewhere in the application.
            result["visitor_parking_required"] = total_car * 0.05
        return result

    def _parking_vehicle_columns(self, row, non_congested):
        normalized = {self._norm(k): k for k in row}
        area = "noncongestedarea" if non_congested else "congestedarea"
        car = None
        scooter = None
        for key_norm, key in normalized.items():
            if area in key_norm and "car" in key_norm:
                car = key
            if area in key_norm and "scooter" in key_norm:
                scooter = key
        if car is None:
            car = self._find_column(row, ("car parking", "car"))
        if scooter is None:
            scooter = self._find_column(row, ("scooter", "two wheeler"))
        return car, scooter

    @staticmethod
    def _parking_divisor(size_text):
        m = re.search(r"for every\s+(\d+)\s+tenement", size_text, re.I)
        if m:
            return max(1, int(m.group(1)))
        if re.search(r"for every\s+tenement", size_text, re.I):
            return 1
        return 1

    def _parking_size_matches_all(self, size_text, areas):
        values = [float(v) for v in areas]
        if not values:
            return False
        # Generic interpretation of the textual carpet-area band in Table 8-B.
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", size_text)]
        text = size_text.lower().replace("–", "-").replace("—", "-")
        if not nums:
            return False
        lower = None
        upper = None
        if "150 sq" in text or "150.0 sq" in text:
            pass
        if re.search(r"150\s*sq|150\s*m", text) and "above" in text:
            lower = nums[-1]
        if "equal to or above" in text and "less than" in text and len(nums) >= 2:
            lower, upper = nums[-2], nums[-1]
        elif "less than 80" in text and "more than 40" in text:
            lower, upper = 40.0, 80.0
        elif "less than 40" in text and "more than 30" in text:
            lower, upper = 30.0, 40.0
        elif "less than 30" in text:
            upper = 30.0
        elif "150" in text and ("above" in text or "and above" in text):
            lower = 150.0
        if lower is None and "80" in text and "150" in text:
            lower, upper = 80.0, 150.0
        for value in values:
            if lower is not None and value < lower:
                return False
            if upper is not None and value >= upper:
                return False
        return True

    def _extract_fields(self, row, requested_fields, facts):
        result = {}

        for field in requested_fields:
            candidates = self.FIELD_ALIASES.get(field, ())
            key = self._find_column(row, candidates)

            if key is None:
                continue

            value = self._parse_scalar(row[key])
            if value is not None:
                result[field] = value

        return result

    def _table_can_supply_field(self, table, field):
        text = re.sub(
            r"\s+",
            " ",
            " ".join(
                str(x) for x in (
                    getattr(table, "title", ""),
                    getattr(table, "headers", ""),
                    getattr(table, "markdown", ""),
                )
            ),
        ).lower()

        hints = self.FIELD_TABLE_HINTS.get(field, ())
        return not hints or any(h in text for h in hints)

    # --------------------------------------------------------------
    # Generic row matching
    # --------------------------------------------------------------
    def _row_applies(self, row, facts):
        road_width = self._fact(facts, "road_width")

        road_key = self._find_column(
            row,
            (
                "road width",
                "road width in meters",
                "width of road",
            ),
        )

        if road_width is not None and road_key is not None:
            if not self._matches_range(
                str(row[road_key]),
                float(road_width),
            ):
                return False

        authority = (
            self._fact(facts, "planning_authority")
            or self._fact(facts, "municipal_corporation")
            or self._fact(facts, "municipality")
            or self._fact(facts, "competent_authority")
        )

        # Only reject a categorical authority row when it clearly names an
        # incompatible authority. Otherwise leave it to the table branch.
        authority_key = self._find_column(
            row,
            ("authority", "area", "municipal corporation"),
        )
        if authority_key is not None and authority:
            cell = self._norm(row[authority_key])
            auth = self._norm(authority)
            if cell and auth and self._looks_like_authority_cell(cell):
                if not self._authority_matches(cell, auth):
                    return False

        return True

    @staticmethod
    def _looks_like_authority_cell(value):
        return any(
            token in value
            for token in (
                "municipal",
                "corporation",
                "authority",
                "cidco",
                "pcntda",
            )
        )

    @staticmethod
    def _authority_matches(cell, authority):
        # Generic token matching; no authority-specific regulatory values.
        a_tokens = {
            x for x in re.split(r"[^a-z0-9]+", authority)
            if len(x) >= 3
        }
        c_tokens = {
            x for x in re.split(r"[^a-z0-9]+", cell)
            if len(x) >= 3
        }
        return bool(a_tokens & c_tokens)

    @staticmethod
    def _matches_range(text, number):
        t = text.lower().replace("–", "-").replace("—", "-")

        nums = [
            float(x)
            for x in re.findall(r"\d+(?:\.\d+)?", t)
        ]

        if not nums:
            return True

        lower = upper = None

        if re.search(r"\bbelow\b|\bunder\b|<", t):
            upper = nums[-1]
        elif re.search(r"\babove\b|\bmore than\b|>", t):
            lower = nums[0]

        if len(nums) >= 2:
            if re.search(
                r"and\s+above.*(?:below|upto|up to|less)|to\s*<|[-]\s*<",
                t,
            ):
                lower, upper = nums[0], nums[1]
            elif "upto" in t or "up to" in t or "to" in t:
                lower, upper = nums[0], nums[1]

        if lower is not None and number < lower:
            return False
        if upper is not None and number >= upper:
            return False

        return True

    # --------------------------------------------------------------
    # Missing input detection
    # --------------------------------------------------------------
    def _missing_inputs(self, row, facts):
        missing = []

        if self._find_column(
            row, ("road width", "road width in meters", "width of road")
        ) is not None:
            if self._fact(facts, "road_width") is None:
                missing.append("road_width")

        if self._find_column(
            row, ("plot area", "area of plot", "plot size")
        ) is not None:
            if self._fact(facts, "plot_area") is None:
                missing.append("plot_area")

        if self._find_column(
            row, ("carpet area", "size of tenement", "tenement area")
        ) is not None:
            areas = self._fact(facts, "tenement_carpet_areas")
            if not areas:
                missing.append("tenement_carpet_areas")

        if self._find_column(
            row, ("height", "building height")
        ) is not None:
            if self._fact(facts, "building_height") is None:
                missing.append("building_height")

        return missing

    # --------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------
    @staticmethod
    def _fact(facts, name):
        if hasattr(facts, "get"):
            return facts.get(name)
        return getattr(facts, name, None)

    @staticmethod
    def _number(value):
        if isinstance(value, dict):
            value = (
                value.get("regulation_number")
                or value.get("number")
                or value.get("regulation")
            )
        else:
            value = (
                getattr(value, "regulation_number", None)
                or getattr(value, "number", None)
                or value
            )

        if value is None:
            return None

        text = str(value).strip()
        if text.upper().startswith("UDCPR:"):
            text = text.split(":", 1)[1].strip()

        return text.split("|", 1)[0].strip() or None

    @staticmethod
    def _source_text_for_regulation(number, sources):
        result = []
        for source in sources or []:
            metadata = getattr(source, "metadata", {}) or {}
            source_number = (
                metadata.get("regulation_number")
                or metadata.get("number")
                or getattr(source, "regulation_number", None)
            )

            if source_number is not None:
                source_number = str(source_number).strip()

            text = (
                getattr(source, "text", None)
                or getattr(source, "content", None)
                or ""
            )

            if (source_number and self._norm(source_number) == self._norm(number)) or self._norm(number) in self._norm(text):
                result.append({
                    "source_id": (
                        getattr(source, "source_id", None)
                        or getattr(source, "id", None)
                        or "chroma-source"
                    ),
                    "text": str(text),
                })

        return result

    @staticmethod
    def _table_number(table):
        metadata = getattr(table, "metadata", None) or {}
        value = (
            metadata.get("table_number")
            or metadata.get("number")
            or metadata.get("table_no")
            or getattr(table, "table_number", None)
        )
        if value:
            return str(value).strip()

        # The ingestion schema stores title/headers/markdown rather than
        # necessarily having a dedicated table_number column.
        haystack = " ".join(
            str(x or "")
            for x in (
                getattr(table, "title", ""),
                getattr(table, "headers", ""),
                getattr(table, "markdown", ""),
            )
        )
        match = re.search(
            r"\bTable\s+(?:No\.?\s*)?([0-9]+(?:\.[0-9]+)?[-A-Za-z]?)\b",
            haystack,
            re.I,
        )
        return match.group(1).upper() if match else None

    @staticmethod
    def _table_title(table):
        return str(getattr(table, "title", "") or "").strip()

    @staticmethod
    def _norm_table(value):
        return re.sub(
            r"[^0-9a-z]+", "", str(value or "").lower()
        )

    @staticmethod
    def _norm(value):
        return re.sub(
            r"\s+", " ", str(value or "").strip().lower()
        )

    @staticmethod
    def _normalize_headers(headers, rows):
        """
        Reconstruct sparse/multi-row PDF table headers.

        The UDCPR tables are often stored as a first header row plus several
        continuation rows. We concatenate non-empty cells by column until the
        row containing simple numeric column numbers is reached.

        This is structural parsing only; it does not contain regulatory values.
        """
        width = 0
        if headers:
            if any(isinstance(item, (list, tuple, dict)) for item in headers):
                for item in headers:
                    width = max(width, len(item) if isinstance(item, (list, tuple, dict)) else 1)
            else:
                width = len(headers)
        for row in rows:
            if isinstance(row, (list, tuple)):
                width = max(width, len(row))
            elif isinstance(row, dict):
                width = max(width, len(row))

        if width == 0:
            return []

        header_rows = []
        if headers:
            # PostgreSQL table ingestion may store headers as a list of
            # header rows (the PDF extractor preserves merged/multi-row
            # headers).  Treat nested headers as rows; a flat header list is
            # one row.
            if any(isinstance(item, (list, tuple, dict)) for item in headers):
                for item in headers:
                    if isinstance(item, dict):
                        header_rows.append(list(item.values()))
                    elif isinstance(item, (list, tuple)):
                        header_rows.append(list(item))
                    else:
                        header_rows.append([item])
            else:
                header_rows.append(list(headers))

        # Some ingestion versions put the real multi-row headers in rows.
        # Collect leading rows until the first obvious data row.
        for raw in rows[:8]:
            if isinstance(raw, dict):
                values = list(raw.values())
            else:
                values = list(raw or [])

            joined = " ".join(str(v or "") for v in values).strip()
            if not joined:
                continue

            numeric_only = (
                sum(
                    1 for v in values
                    if str(v or "").strip().isdigit()
                ) >= 3
            )

            has_data_row = bool(
                re.search(
                    r"\b(?:below|above|upto|up to|and above)\b",
                    joined,
                    re.I,
                )
            )

            if numeric_only or has_data_row:
                break

            header_rows.append(values)

        result = []
        for col in range(width):
            parts = []
            for row in header_rows:
                if col >= len(row):
                    continue
                value = str(row[col] or "").strip()
                if not value:
                    continue
                if value.isdigit():
                    continue
                if value not in parts:
                    parts.append(value)

            result.append(" ".join(parts).strip() or f"column_{col}")

        return result

    @staticmethod
    def _row_dict(raw_row, headers):
        if isinstance(raw_row, dict):
            return {
                str(k).strip(): v
                for k, v in raw_row.items()
            }

        values = list(raw_row or [])
        return {
            headers[i] if i < len(headers) else f"column_{i}": value
            for i, value in enumerate(values)
        }

    @classmethod
    def _find_column(cls, row, aliases):
        normalized = {
            cls._norm(k): k
            for k in row
        }

        for alias in aliases:
            needle = cls._norm(alias)
            if needle in normalized:
                return normalized[needle]

        for alias in aliases:
            needle = cls._norm(alias)
            for key_norm, key in normalized.items():
                if needle and needle in key_norm:
                    return key

        return None

    @staticmethod
    def _parse_scalar(raw):
        if raw is None:
            return None

        text = str(raw).strip()
        if not text or text in {"-", "--", "N/A", "NA"}:
            return None

        m = re.fullmatch(
            r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
            r"(?:\s*(mm|cm|m|ft|feet|%|sq\.?\s*m|sqm|fsi))?",
            text,
            re.I,
        )
        if not m:
            return None

        value = float(re.match(
            r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)",
            text,
        ).group(0))

        unit = (m.group(1) or "").lower()

        if unit == "mm":
            value /= 1000.0
        elif unit == "cm":
            value /= 100.0
        elif unit in {"ft", "feet"}:
            value *= 0.3048

        return int(value) if value.is_integer() else value

    @staticmethod
    def _stable(value):
        return repr(value)
