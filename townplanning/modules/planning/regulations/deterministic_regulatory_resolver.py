from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeterministicResolution:
    status: str
    constraints: list[dict[str, Any]] = field(default_factory=list)
    values: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DeterministicRegulatoryResolver:
    """Resolve regulatory values only from supplied PostgreSQL evidence.

    This class deliberately contains no UDCPR numeric constants.  It only
    interprets structured/table data already stored in PostgreSQL and matches
    rows against PlanningFacts.  OpenAI/Chroma are not called here.
    """

    FIELD_ALIASES = {
        "basic_fsi": ["basic_fsi", "basic permissible fsi", "basic fsi"],
        "premium_fsi": ["premium_fsi", "fsi on payment of premium", "premium fsi", "fsi on premium"],
        "tdr_fsi": ["tdr_fsi", "tdr fsi", "tdr"],
        "maximum_fsi": ["maximum_fsi", "maximum permissible fsi", "maximum building potential", "maximum building potential on plot", "maximum fsi", "max fsi"],
        "front_setback": ["front_setback", "front setback", "front margin", "front marginal distance"],
        "rear_setback": ["rear_setback", "rear setback", "rear margin", "rear marginal distance"],
        "side_setback": ["side_setback", "side setback", "side margin", "side marginal distance"],
        "side_setback_left": ["side_setback_left", "left setback", "left side setback"],
        "side_setback_right": ["side_setback_right", "right setback", "right side setback"],
        "side_rear_margins": ["side_rear_margins", "side and rear margins", "side & rear margins", "side rear margins"],
        "maximum_ground_coverage": ["maximum_ground_coverage", "ground coverage", "maximum coverage", "coverage percent", "maximum ground coverage"],
        "maximum_height_m": ["maximum_height_m", "maximum height", "height limit", "maximum building height", "building height"],
        "maximum_storeys": ["maximum_storeys", "maximum storeys", "maximum stories", "max storeys", "number of storeys"],
        "car_parking_required": ["car_parking_required", "parking requirement", "parking required", "car parking", "cars required", "car parking spaces"],
        "two_wheeler_parking_required": ["two_wheeler_parking_required", "two wheeler parking", "scooter parking", "motorcycle parking"],
        "visitor_parking_required": ["visitor_parking_required", "visitor parking"],
        "parking_area_required_m2": ["parking_area_required_m2", "parking area required", "parking area", "parking area in sq.m"],
        "fire_access_required": ["fire_access_required", "fire access", "fire tender access", "fire engine access"],
        "fire_lift_required": ["fire_lift_required", "fire lift", "fireman lift"],
        "fire_staircase_required": ["fire_staircase_required", "fire staircase", "fire escape staircase"],
        "minimum_exit_count": ["minimum_exit_count", "minimum number of exits", "number of exits", "exit count"],
        "minimum_exit_width_m": ["minimum_exit_width_m", "minimum exit width", "exit width"],
        "staircase_count": ["staircase_count", "number of staircases", "staircase count"],
        "staircase_width_m": ["staircase_width_m", "staircase width", "stair width"],
        "corridor_width_m": ["corridor_width_m", "corridor width"],
        "lift_required": ["lift_required", "lift required", "provision of lift", "lift provision"],
        "lift_count": ["lift_count", "number of lifts", "lift count"],
        "accessible_entrance_required": ["accessible_entrance_required", "accessible entrance", "accessible entry"],
        "ramp_required": ["ramp_required", "ramp required"],
        "ramp_width_m": ["ramp_width_m", "ramp width"],
        "ramp_gradient": ["ramp_gradient", "ramp gradient", "gradient of ramp"],
        "minimum_open_space_m2": ["minimum_open_space_m2", "minimum open space", "open space requirement"],
        "recreational_open_space_m2": ["recreational_open_space_m2", "recreational open space"],
        "amenity_space_m2": ["amenity_space_m2", "amenity space"],
        "road_widening": ["road_widening", "road widening"],
        "reservation_present": ["reservation_present", "reservation"],
    }

    def resolve(
        self,
        *,
        facts: Any,
        selected_regulations: list[Any],
        sources: list[Any],
        requested_fields: list[str],
    ) -> DeterministicResolution:
        fact_values = self._facts(facts)
        selected = {self._reg_number(x) for x in (selected_regulations or [])}
        selected.discard(None)
        sources = [s for s in (sources or []) if self._reg_number(s) in selected or not selected]

        result = DeterministicResolution(status="INSUFFICIENT_RULE_DATA")
        seen: set[tuple[str, str]] = set()

        for source in sources:
            text = str(getattr(source, "text", "") or "").strip()
            if not text:
                continue
            reg = self._reg_number(source)
            source_id = getattr(source, "source_id", None) or "postgresql-source"

            records = self._records(text)
            if records:
                for record in records:
                    self._resolve_record(record, source, reg, source_id, fact_values, requested_fields, result, seen)

            # Also support scalar labelled provisions outside tables.
            self._resolve_prose(text, source, reg, source_id, fact_values, requested_fields, result, seen)

        if result.constraints:
            result.status = "RESOLVED"
            for c in result.constraints:
                result.values[c["field"]] = c["value"]
        else:
            result.status = "INSUFFICIENT_RULE_DATA"
            if selected:
                result.errors.append(
                    "No deterministic constraint value could be resolved from the selected PostgreSQL sources for the supplied PlanningFacts."
                )
        return result

    @staticmethod
    def _facts(facts: Any) -> dict[str, Any]:
        if hasattr(facts, "to_dict"):
            d = dict(facts.to_dict())
        else:
            d = dict(vars(facts))
        aliases = {
            "roadWidth": "road_width", "plotArea": "plot_area",
            "buildingType": "building_type", "buildingUse": "building_use",
            "occupancyType": "occupancy_type", "cityName": "city",
            "districtName": "district", "planningAuthority": "planning_authority",
            "municipalCorporation": "municipal_corporation",
        }
        for a, k in aliases.items():
            if k in d and d[k] is not None:
                d.setdefault(a, d[k])
        return d

    @staticmethod
    def _reg_number(obj: Any) -> str | None:
        if obj is None:
            return None
        if isinstance(obj, str):
            return obj.strip() or None
        for name in ("regulation_number", "number", "regulation"):
            value = getattr(obj, name, None)
            if value:
                text = str(value).strip()
                if text.upper().startswith("UDCPR:"):
                    text = text.split(":", 1)[1].strip()
                return text.split("|", 1)[0].strip() or None
        if isinstance(obj, dict):
            for name in ("regulation_number", "number", "regulation"):
                if obj.get(name):
                    return str(obj[name]).strip()
        return None

    def _records(self, text: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        # Structured JSON/Python dictionaries already present in the source.
        candidates = re.findall(r"\{[^{}]{20,}\}", text, flags=re.S)
        for raw in candidates:
            value = None
            try:
                value = json.loads(raw)
            except Exception:
                try:
                    value = ast.literal_eval(raw)
                except Exception:
                    pass
            if isinstance(value, dict):
                records.append(value)

        for marker in ("rows", "data", "table_rows"):
            match = re.search(rf"['\"]{marker}['\"]\s*:\s*(\[[\s\S]*?\])", text, re.I)
            if match:
                try:
                    value = json.loads(match.group(1))
                except Exception:
                    try:
                        value = ast.literal_eval(match.group(1))
                    except Exception:
                        value = None
                if isinstance(value, list):
                    records.extend(x for x in value if isinstance(x, dict))

        # PostgreSQL table serialization.  The PDF/table extractor often
        # stores multi-line headers as ROW[0], ROW[1], ... and then stores a
        # numeric column-number row before the real data.  The old parser
        # treated those header rows as data, which produced values such as
        # 2, 9, 12, 70 and 50 for unrelated regulatory fields.  Reconstruct
        # the column labels first, discard the header/column-number rows, and
        # only expose real data rows to the resolver.
        row_starts = list(re.finditer(r"^\s*ROW\[(\d+)\]:\s*(.*)$", text, flags=re.I | re.M))
        if row_starts:
            native_rows: list[dict[int, str]] = []
            for pos, match in enumerate(row_starts):
                start_pos = match.start(2)
                end_pos = row_starts[pos + 1].start() if pos + 1 < len(row_starts) else len(text)
                block = text[start_pos:end_pos]
                cells: dict[int, str] = {}
                for cm in re.finditer(
                    r"C\[(\d+)\]\s*=\s*(.*?)(?=\s*\|\s*C\[\d+\]\s*=|$)",
                    block,
                    flags=re.S,
                ):
                    cells[int(cm.group(1))] = re.sub(r"\s+", " ", cm.group(2)).strip()
                native_rows.append(cells)

            def nonempty(row: dict[int, str]) -> list[str]:
                return [str(v).strip() for _, v in sorted(row.items()) if str(v).strip()]

            def is_column_number_row(row: dict[int, str]) -> bool:
                vals = nonempty(row)
                if len(vals) < 2:
                    return False
                nums = []
                for v in vals:
                    if not re.fullmatch(r"\d+", v):
                        return False
                    nums.append(int(v))
                return nums == list(range(1, len(nums) + 1))

            # Locate the first column-number row.  Everything before it is a
            # multi-row header; everything after it is data (until the next
            # obvious table header/section).
            number_row_index = next(
                (i for i, row in enumerate(native_rows) if is_column_number_row(row)),
                None,
            )

            if number_row_index is not None:
                header_rows = native_rows[:number_row_index]
                data_rows = native_rows[number_row_index + 1:]
            else:
                # Some tables have no numbered header row.  Keep the first
                # rows as headers only when they contain descriptive text and
                # later rows contain a clear numeric first column.
                first_data = None
                for i, row in enumerate(native_rows):
                    vals = nonempty(row)
                    if not vals:
                        continue
                    if re.fullmatch(r"\d+(?:\.\d+)?", vals[0]) and len(vals) >= 2:
                        first_data = i
                        break
                if first_data is None:
                    header_rows, data_rows = [], native_rows
                else:
                    header_rows, data_rows = native_rows[:first_data], native_rows[first_data:]

            # Merge multi-row headers column-wise.  Empty cells are intentional
            # merged-cell placeholders in the source and must not become field
            # values themselves.
            max_col = max((max(r.keys()) for r in native_rows if r), default=-1)
            headers: dict[int, str] = {}
            for col in range(max_col + 1):
                parts: list[str] = []
                for row in header_rows:
                    value = str(row.get(col, "") or "").strip()
                    if not value:
                        continue
                    if re.fullmatch(r"\(?\d+\)?", value):
                        continue
                    if value not in parts:
                        parts.append(value)
                headers[col] = re.sub(r"\s+", " ", " ".join(parts)).strip()

            # Propagate branch headings through merged cells.  This is useful
            # for tables such as 6-G where premium/TDR/max columns occur under
            # two authority branches.
            branch = ""
            branch_by_col: dict[int, str] = {}
            for col in range(max_col + 1):
                h = headers.get(col, "").lower()
                if "municipal corporation" in h or "cidco" in h:
                    branch = "municipal"
                elif "remaining authorities" in h or "remaining authority" in h:
                    branch = "remaining"
                if branch:
                    branch_by_col[col] = branch

            for row in data_rows:
                if not row:
                    continue
                # Do not expose rows that are clearly another column-number
                # header or empty separator.
                if is_column_number_row(row):
                    continue
                semantic: dict[str, Any] = {}
                for col, value in sorted(row.items()):
                    value = str(value).strip()
                    if not value:
                        continue
                    header = headers.get(col, "").strip()
                    if header:
                        semantic[header] = value
                    # Preserve stable source-column keys for structural
                    # fallback; they are never interpreted as regulatory
                    # field names by themselves.
                    semantic[f"column_{col}"] = value
                    if branch_by_col.get(col) == "municipal":
                        semantic[f"municipal::{header}"] = value
                    elif branch_by_col.get(col) == "remaining":
                        semantic[f"remaining::{header}"] = value
                if semantic:
                    records.append(semantic)

        # Markdown/pipe tables.  Only true markdown tables are parsed here;
        # ordinary prose containing a pipe is ignored.
        lines = [x.strip() for x in text.splitlines() if "|" in x]
        for i in range(len(lines) - 1):
            headers = self._cells(lines[i])
            separator = self._cells(lines[i + 1])
            if len(headers) < 2 or not all(self._is_separator(c) for c in separator):
                continue
            for row_line in lines[i + 2:]:
                cells = self._cells(row_line)
                if len(cells) < 2:
                    break
                row = {
                    self._norm(h): cells[j].strip() if j < len(cells) else ""
                    for j, h in enumerate(headers)
                    if str(h).strip()
                }
                if row:
                    records.append(row)
        return records

    @staticmethod
    def _cells(line: str) -> list[str]:
        return [x.strip() for x in line.strip().strip("|").split("|")]

    @staticmethod
    def _is_separator(cell: str) -> bool:
        return bool(re.fullmatch(r":?-{2,}:?", cell.strip()))

    @staticmethod
    def _norm(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

    def _resolve_record(self, record: dict[str, Any], source: Any, reg: str | None, source_id: str,
                        facts: dict[str, Any], requested_fields: list[str], result: DeterministicResolution,
                        seen: set[tuple[str, str]]) -> None:
        normalized = {self._norm(k): v for k, v in record.items()}
        if not self._row_applies(normalized, facts):
            return
        for field in requested_fields:
            aliases = self.FIELD_ALIASES.get(field, [field])
            for alias in aliases:
                alias_n = self._norm(alias)
                for key, raw in normalized.items():
                    if key == alias_n or alias_n in key or key in alias_n:
                        value, unit = self._clean_value(raw)
                        if value is not None:
                            self._add(field, value, unit, source, reg, source_id, result, seen)
                            break
                else:
                    continue
                break

    def _row_applies(self, row: dict[str, Any], facts: dict[str, Any]) -> bool:
        # Only reject a row when an explicit dimension clearly excludes the fact.
        for key, fact_key in (("min road width m", "road_width"), ("minimum road width m", "road_width"),
                              ("road width", "road_width"), ("min road width", "road_width")):
            if key in row and facts.get(fact_key) is not None:
                if not self._matches_number_range(str(row[key]), float(facts[fact_key])):
                    return False
        for key, fact_key in (("plot size in sq m", "plot_area"), ("plot size", "plot_area"),
                              ("carpet area", "tenement_carpet_area"), ("height", "building_height")):
            if key in row and facts.get(fact_key) is not None:
                if not self._matches_number_range(str(row[key]), float(facts[fact_key])):
                    return False
        # Authority/zone/use dimensions, if present in the row, must match when facts are known.
        for aliases, fact_keys in [
            (["planning authority", "authority", "municipality"], ["planning_authority", "municipal_corporation", "municipality"]),
            (["zone", "zone type", "land use"], ["zone", "zone_type", "land_use_zone"]),
            (["building use", "use", "occupancy"], ["building_use", "occupancy_type", "building_type"]),
        ]:
            row_values = [row[a] for a in aliases if a in row and row[a]]
            fact_values = [str(facts[k]).lower() for k in fact_keys if facts.get(k) is not None]
            if row_values and fact_values:
                text = " ".join(map(str, row_values)).lower()
                if not any(v in text or text in v for v in fact_values):
                    return False
        return True

    @staticmethod
    def _matches_number_range(text: str, number: float) -> bool:
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))]
        if not nums:
            return True
        low = text.lower().replace("–", "-").replace("—", "-")
        if len(nums) >= 2:
            if ("above" in low or ">" in low) and ("upto" in low or "up to" in low or "to" in low or "<" in low):
                return nums[0] < number <= nums[1]
            if "to" in low or "-" in low or "between" in low:
                return nums[0] <= number <= nums[1]
            return nums[0] <= number <= nums[1]
        n = nums[0]
        if "above" in low or ">" in low or ">=" in low:
            return number >= n
        if "below" in low or "upto" in low or "up to" in low or "<" in low or "less" in low:
            return number <= n
        return True

    def _resolve_prose(self, text: str, source: Any, reg: str | None, source_id: str,
                       facts: dict[str, Any], requested_fields: list[str], result: DeterministicResolution,
                       seen: set[tuple[str, str]]) -> None:
        # Prose fallback is deliberately conservative.  A field is accepted
        # only when the source explicitly labels a value.  This prevents
        # unrelated numbers in clauses (road widths, dates, percentages,
        # regulation numbers, etc.) from becoming FSI/setback/parking values.
        for field in requested_fields:
            aliases = self.FIELD_ALIASES.get(field, [field])
            for alias in aliases:
                pattern = re.escape(alias).replace(r"\ ", r"\s+")
                match = re.search(
                    rf"(?<![\w]){pattern}(?![\w])\s*(?:is|are|shall be|shall|=|:)\s*"
                    rf"([0-9]+(?:\.[0-9]+)?\s*(?:m|mm|cm|%|feet|ft|sq\.?\s*m|sqm|fsi)?|"
                    rf"yes|no|required|not required|mandatory)",
                    text,
                    re.I,
                )
                if not match:
                    continue
                value, unit = self._clean_value(match.group(1))
                if value is not None:
                    self._add(field, value, unit, source, reg, source_id, result, seen)
                    break

    @staticmethod
    def _clean_value(raw: Any) -> tuple[Any | None, str | None]:
        if raw is None or isinstance(raw, (dict, list)):
            return None, None
        text = str(raw).strip()
        if not text or text in {"-", "--", "N/A", "NA"}:
            return None, None
        if re.fullmatch(r"\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?", text):
            return text, None
        m = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(mm|cm|m|ft|feet|%|sq\.?m|sqm|fsi)?\s*", text, re.I)
        if not m:
            if text.lower() in {"yes", "no", "required", "not required", "mandatory"}:
                return text.lower(), None
            return None, None
        value = float(m.group(1))
        if value.is_integer():
            value = int(value)
        unit = (m.group(2) or "").lower()
        if unit == "mm":
            value, unit = value / 1000.0, "m"
        elif unit == "cm":
            value, unit = value / 100.0, "m"
        elif unit in {"ft", "feet"}:
            value, unit = value * 0.3048, "m"
        elif unit == "sq.m" or unit == "sqm":
            unit = "m2"
        elif unit == "fsi":
            unit = "fsi"
        elif unit == "%":
            unit = "%"
        else:
            unit = unit or None
        return value, unit

    @staticmethod
    def _add(field: str, value: Any, unit: str | None, source: Any, reg: str | None, source_id: str,
             result: DeterministicResolution, seen: set[tuple[str, str]]) -> None:
        key = (field, json.dumps(value, sort_keys=True, default=str) + ":" + str(unit))
        if key in seen:
            return
        seen.add(key)
        result.constraints.append({
            "field": field,
            "value": value,
            "unit": unit,
            "source_id": source_id,
            "regulation_number": reg,
            "condition": {},
            "confidence": "authoritative",
        })
