"""
Generic PDF table extraction.

Source extraction only.

This module does NOT:
    - calculate FSI
    - calculate setbacks
    - calculate height
    - calculate floors
    - calculate parking
    - interpret regulatory applicability
    - select regulatory rows
    - infer regulatory values

Special handling:
    PyMuPDF may fail to recognize a continuation row on a
    multi-page table. Missing rows are recovered directly from
    PDF word coordinates.
"""

from __future__ import annotations

import re
from typing import Any

from townplanning.modules.regulations.ingestion.table import (
    ExtractedTable,
)


class TableExtractor:

    def extract(
        self,
        reader,
        page_number: int,
    ) -> list[ExtractedTable]:

        document = reader._document
        page = document.load_page(
            page_number - 1
        )

        raw_tables = self._find_tables(page)

        tables = self._convert_tables(
            raw_tables,
            page_number,
        )

        tables = self._deduplicate_tables(
            tables
        )

        tables = self._recover_continuation_rows(
            page,
            page_number,
            tables,
        )

        return tables

    # ================================================================
    # PYMuPDF TABLE DETECTION
    # ================================================================

    def _find_tables(
        self,
        page: Any,
    ) -> list[Any]:

        try:
            finder = page.find_tables()

            tables = list(
                getattr(
                    finder,
                    "tables",
                    [],
                )
                or []
            )

            if tables:
                return tables

        except Exception:
            pass

        try:
            finder = page.find_tables(
                strategy="text"
            )

            return list(
                getattr(
                    finder,
                    "tables",
                    [],
                )
                or []
            )

        except Exception:
            return []

    def _convert_tables(
        self,
        tables: list[Any],
        page_number: int,
    ) -> list[ExtractedTable]:

        output = []

        for index, table in enumerate(
            tables,
            start=1,
        ):
            extracted = self._extract_table(
                table,
                page_number,
                index,
            )

            if extracted is not None:
                output.append(
                    extracted
                )

        return output

    def _extract_table(
        self,
        table: Any,
        page_number: int,
        index: int,
    ) -> ExtractedTable | None:

        try:
            data = table.extract()
        except Exception:
            return None

        if not data:
            return None

        normalized = self._normalize_matrix(
            data
        )

        if not normalized:
            return None

        try:
            markdown = (
                table.to_markdown()
                if hasattr(
                    table,
                    "to_markdown",
                )
                else ""
            ) or ""
        except Exception:
            markdown = ""

        headers = list(
            normalized[0]
        )

        rows = [
            list(row)
            for row in normalized[1:]
        ]

        bbox = self._extract_bbox(
            table
        )

        metadata = {
            "extractor":
                "pymupdf_table_extractor",

            "source_page":
                page_number,

            "source_table_index":
                index,

            "row_count":
                len(rows),

            "column_count":
                len(headers),

            "has_markdown":
                bool(markdown),

            "has_bbox":
                bbox is not None,

            "header_detection": {
                "method":
                    "first_row",
                "semantic_validation":
                    False,
            },
        }

        return ExtractedTable(
            page=page_number,
            index=index,
            title="",
            headers=headers,
            header_rows=[headers],
            rows=rows,
            markdown=markdown,
            bbox=bbox,
            metadata=metadata,
        )

    # ================================================================
    # DUPLICATE DETECTION
    # ================================================================

    def _deduplicate_tables(
        self,
        tables: list[ExtractedTable],
    ) -> list[ExtractedTable]:

        if len(tables) <= 1:
            return tables

        result = []

        for table in tables:

            duplicate = False

            for existing in result:

                if (
                    table.page
                    == existing.page
                    and
                    self._table_similarity(
                        table,
                        existing,
                    )
                ):
                    duplicate = True
                    break

            if not duplicate:
                result.append(
                    table
                )

        return result

    def _table_similarity(
        self,
        a: ExtractedTable,
        b: ExtractedTable,
    ) -> bool:

        ca = len(a.headers)
        cb = len(b.headers)

        if abs(ca - cb) > 2:
            return False

        ra = len(a.rows)
        rb = len(b.rows)

        if ra < 5 or rb < 5:
            return False

        return (
            ra > rb * 2
            or rb > ra * 2
        )

    # ================================================================
    # CONTINUATION RECOVERY
    # ================================================================

    def _recover_continuation_rows(
        self,
        page: Any,
        page_number: int,
        tables: list[ExtractedTable],
    ) -> list[ExtractedTable]:

        if not tables:
            return tables

        words = self._get_words(page)

        if not words:
            return tables

        for table in tables:

            existing_numbers = self._extract_row_numbers(
                table.rows
            )

            header_number = self._row_number(
                table.headers
            )

            # --------------------------------------------------------
            # Continuation-page case
            #
            # PyMuPDF can mistake the first numbered continuation row
            # for the table header. For Table 6-D page 127:
            #
            #     headers = row 6
            #     rows    = row 7
            #
            # The preceding physical row (row 5) is still present in
            # the PDF but is omitted from the detected table.
            #
            # Recover ONLY the immediately preceding numbered row.
            # Do not attempt rows 1..5 because those belong to the
            # previous page.
            # --------------------------------------------------------
            recovery_numbers = []

            if header_number is not None:

                candidate = header_number - 1

                if candidate >= 1:

                    # Confirm that the candidate is physically present
                    # on this page and immediately precedes the detected
                    # header row.
                    header_y = self._find_existing_row_y(
                        words,
                        header_number,
                    )

                    if header_y is not None:

                        candidate_y = self._find_existing_row_y(
                            words,
                            candidate,
                        )

                        if (
                            candidate_y is not None
                            and candidate_y < header_y - 2
                        ):
                            recovery_numbers = [
                                candidate
                            ]

            # --------------------------------------------------------
            # If there is no numbered header, retain the existing
            # conservative behaviour for a genuinely missing prefix.
            # --------------------------------------------------------
            if (
                not recovery_numbers
                and header_number is None
            ):

                if not existing_numbers:
                    continue

                first_existing = min(
                    existing_numbers
                )

                if first_existing <= 1:
                    continue

                missing_numbers = list(
                    range(
                        1,
                        first_existing,
                    )
                )

                if len(missing_numbers) > 3:
                    continue

                first_row_y = self._find_existing_row_y(
                    words,
                    first_existing,
                )

                if first_row_y is None:
                    continue

                anchors = self._derive_column_anchors(
                    words,
                    first_existing,
                    first_row_y,
                    table,
                )

                if not anchors:
                    continue

                recovered = []

                for number in missing_numbers:

                    row = self._recover_row_before(
                        words=words,
                        row_number=number,
                        upper_y=first_row_y,
                        anchors=anchors,
                        column_count=len(anchors),
                    )

                    if row is not None:
                        recovered.append(row)

                if recovered:
                    table.rows = (
                        recovered
                        + list(table.rows)
                    )

                    metadata = dict(
                        getattr(
                            table,
                            "metadata",
                            {},
                        )
                        or {}
                    )

                    metadata[
                        "recovered_from_page_text"
                    ] = True

                    metadata[
                        "recovery_method"
                    ] = "pdf_word_coordinates"

                    metadata[
                        "recovered_row_count"
                    ] = len(recovered)

                    table.metadata = metadata

                continue

            # --------------------------------------------------------
            # Continuation header case.
            #
            # Use the detected header row as the upper boundary for
            # recovering the preceding row.
            # --------------------------------------------------------
            if not recovery_numbers:
                continue

            upper_number = header_number

            upper_y = self._find_existing_row_y(
                words,
                upper_number,
            )

            if upper_y is None:
                continue

            anchors = self._derive_column_anchors(
                words,
                upper_number,
                upper_y,
                table,
            )

            if not anchors:
                continue

            recovered = []

            for number in recovery_numbers:

                row = self._recover_row_before(
                    words=words,
                    row_number=number,
                    upper_y=upper_y,
                    anchors=anchors,
                    column_count=len(anchors),
                )

                if row is not None:
                    recovered.append(row)

            # --------------------------------------------------------
            # Reclassify the detected numbered header as a real data row.
            # --------------------------------------------------------
            header_as_row = list(table.headers)

            table.rows = (
                recovered
                + [header_as_row]
                + list(table.rows)
            )

            table.headers = [
                ""
                for _ in table.headers
            ]

            table.header_rows = []

            metadata = dict(
                getattr(
                    table,
                    "metadata",
                    {},
                )
                or {}
            )

            metadata[
                "continuation_header_reclassified"
            ] = True

            if recovered:

                metadata[
                    "recovered_from_page_text"
                ] = True

                metadata[
                    "recovery_method"
                ] = "pdf_word_coordinates"

                metadata[
                    "recovered_row_count"
                ] = len(recovered)

            table.metadata = metadata

        return tables

    # ================================================================
    # FIND EXISTING ROW POSITION
    # ================================================================

    def _find_existing_row_y(
        self,
        words: list[tuple],
        row_number: int,
    ) -> float | None:

        candidates = []

        for word in words:

            if len(word) < 5:
                continue

            text = str(
                word[4]
            ).strip()

            if text != str(
                row_number
            ):
                continue

            x0 = float(
                word[0]
            )

            y0 = float(
                word[1]
            )

            # Row numbers in the first column are
            # normally near the left side of the page.
            if x0 <= 165:
                candidates.append(
                    (
                        y0,
                        x0,
                    )
                )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0]
        )

        return candidates[0][0]

    # ================================================================
    # COLUMN ANCHORS
    # ================================================================

    def _derive_column_anchors(
        self,
        words: list[tuple],
        row_number: int,
        row_y: float,
        table: ExtractedTable,
    ) -> list[float] | None:

        """
        Derive logical table-column X anchors from the PDF geometry.

        The continuation page can contain multiline cells, so anchors
        must come from the horizontal structure of the detected table
        rather than treating every word position as a column.

        No regulatory values are hardcoded.
        """

        expected = len(table.headers)

        if expected <= 0:
            return None

        # ------------------------------------------------------------
        # 1. Prefer the actual table bounding box.
        # ------------------------------------------------------------
        bbox = self._extract_bbox(table)

        table_x0 = None
        table_x1 = None

        if bbox is not None:
            table_x0 = float(bbox[0])
            table_x1 = float(bbox[2])

        # ------------------------------------------------------------
        # 2. Find the first real detected row (row 6 in the affected
        #    Table 6-D page) and collect its baseline words.
        # ------------------------------------------------------------
        baseline_words = []

        for word in words:
            if len(word) < 5:
                continue

            x0 = float(word[0])
            y0 = float(word[1])
            text = str(word[4]).strip()

            if not text:
                continue

            if abs(y0 - row_y) > 2.5:
                continue

            if table_x0 is not None:
                if x0 < table_x0 - 15:
                    continue

            if table_x1 is not None:
                if x0 > table_x1 + 15:
                    continue

            baseline_words.append(word)

        if not baseline_words:
            return None

        # ------------------------------------------------------------
        # 3. Candidate X positions.
        #
        # Keep positions separated by at least 8 points. This removes
        # punctuation/adjacent words but preserves genuine table cells.
        # ------------------------------------------------------------
        candidates = []

        for word in sorted(
            baseline_words,
            key=lambda item: float(item[0]),
        ):
            x = float(word[0])

            if not candidates or x - candidates[-1] >= 8.0:
                candidates.append(x)

        if len(candidates) < 2:
            return None

        # ------------------------------------------------------------
        # 4. The continuation table normally has one first word per
        #    logical column. Select the expected number of candidates
        #    while preserving the complete horizontal span.
        #
        #    Do NOT simply take candidates[:expected], because a
        #    multiline/merged first cell can introduce misleading
        #    positions before later numeric columns.
        # ------------------------------------------------------------
        if len(candidates) > expected:
            selected = None

            # Find a contiguous window of `expected` anchors whose
            # horizontal span best matches the detected table span.
            if table_x0 is not None and table_x1 is not None:
                target_span = table_x1 - table_x0

                best_score = None

                for i in range(
                    0,
                    len(candidates) - expected + 1,
                ):
                    window = candidates[
                        i:i + expected
                    ]

                    span = window[-1] - window[0]

                    # Prefer windows that cover most of the detected
                    # table width without extending beyond it.
                    span_error = abs(
                        span - target_span
                    )

                    left_error = abs(
                        window[0] - table_x0
                    )

                    right_error = abs(
                        window[-1] - table_x1
                    )

                    score = (
                        span_error
                        + 0.5 * left_error
                        + 0.5 * right_error
                    )

                    if (
                        best_score is None
                        or score < best_score
                    ):
                        best_score = score
                        selected = window

            if selected is not None:
                candidates = selected
            else:
                # Conservative fallback: retain the leftmost expected
                # positions, matching the historical behaviour.
                candidates = candidates[:expected]

        # ------------------------------------------------------------
        # 5. For the affected continuation page, the detected row may
        #    have fewer visible words than logical columns. If that
        #    happens, use the table's bounding-box geometry to complete
        #    the anchors.
        # ------------------------------------------------------------
        if len(candidates) < expected:
            if (
                table_x0 is None
                or table_x1 is None
                or expected < 2
            ):
                return None

            span = table_x1 - table_x0
            step = span / float(expected - 1)

            generated = [
                table_x0 + i * step
                for i in range(expected)
            ]

            # Use detected candidates where possible, while retaining
            # the expected number of logical columns.
            anchors = generated

            for i, candidate in enumerate(candidates):
                if i < len(anchors):
                    anchors[i] = candidate

            return anchors

        return candidates
    # ================================================================
    # RECOVER MISSING ROW
    # ================================================================

    def _recover_row_before(
        self,
        words: list[tuple],
        row_number: int,
        upper_y: float,
        anchors: list[float],
        column_count: int,
    ) -> list[str] | None:

        """
        Recover a missing row whose source text occurs immediately
        before the first row recognized by PyMuPDF.

        The method locates the actual row-number word and collects
        source words until the next numbered row.
        """

        starts = []

        for word in words:

            if len(word) < 5:
                continue

            text = str(
                word[4]
            ).strip()

            if text != str(
                row_number
            ):
                continue

            x0 = float(
                word[0]
            )

            y0 = float(
                word[1]
            )

            # Row number should be in first column.
            if x0 > 165:
                continue

            # It must be above the known first row.
            if y0 >= upper_y - 2:
                continue

            starts.append(
                (
                    y0,
                    x0,
                )
            )

        if not starts:
            return None

        # The nearest matching row number above the known
        # continuation row is the best candidate.
        starts.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        start_y, start_x = starts[0]

        # Find the next numbered row boundary.
        next_y = upper_y

        for word in words:

            if len(word) < 5:
                continue

            text = str(
                word[4]
            ).strip()

            if not re.fullmatch(
                r"[1-9][0-9]?",
                text,
            ):
                continue

            y = float(
                word[1]
            )

            x = float(
                word[0]
            )

            if (
                y > start_y + 2
                and y <= upper_y + 2
                and x <= 165
            ):
                next_y = min(
                    next_y,
                    y,
                )

        row_words = []

        for word in words:

            if len(word) < 5:
                continue

            x0 = float(
                word[0]
            )

            y0 = float(
                word[1]
            )

            if y0 < start_y - 3:
                continue

            if y0 >= next_y - 2:
                continue

            # Restrict to the table region.
            if x0 < anchors[0] - 15:
                continue

            if x0 > anchors[-1] + 80:
                continue

            text = str(
                word[4]
            ).strip()

            if text:
                row_words.append(
                    word
                )

        if not row_words:
            return None

        # ------------------------------------------------------------
        # Assign words to logical columns.
        #
        # Continuation rows can contain vertically wrapped text.
        # In particular, the description cell may contain words whose
        # X positions span what would otherwise look like an additional
        # column. Therefore the first numeric/table column is used as
        # the right boundary of the description cell.
        # ------------------------------------------------------------

        cells = [
            []
            for _ in range(column_count)
        ]

        if column_count < 2:
            return None

        # The first anchor represents the beginning of the description
        # area in the detected continuation table. The next genuine
        # table column is the first numeric column.
        #
        # Ignore spurious X positions generated by wrapped text inside
        # the description. We identify the first numeric column from
        # the source words themselves.
        description_x = anchors[0]

        numeric_candidates = []

        for word in row_words:
            if len(word) < 5:
                continue

            x0 = float(word[0])
            value = str(word[4]).strip()

            if not value:
                continue

            # Numeric-looking source word.
            if re.fullmatch(
                r"[-+]?\d+(?:\.\d+)?",
                value,
            ):
                numeric_candidates.append(
                    (x0, value)
                )

        # The first numeric column should be to the right of the
        # description. Use the leftmost numeric X after the description
        # anchor. This is source-derived and does not contain a
        # regulatory value.
        first_numeric_x = None

        for x0, value in sorted(
            numeric_candidates,
            key=lambda item: item[0],
        ):
            if x0 > description_x + 25:
                first_numeric_x = x0
                break

        if first_numeric_x is None:
            # Fall back to the second anchor only if no numeric source
            # word can establish the boundary.
            first_numeric_x = anchors[1]

        # Description words belong to column 0/1 depending on whether
        # the table exposes an explicit serial-number column.
        #
        # Our recovered continuation table has the logical schema:
        #
        #   serial | description | numeric... | remarks
        #
        # The detected table has eight columns, while the first useful
        # anchor starts at the description position. Put the recovered
        # serial number explicitly in column 0 and start description
        # grouping at column 1.
        serial_column = 0
        description_column = 1

        # Collect the actual row number separately.
        serial_words = []

        for word in row_words:
            if len(word) < 5:
                continue

            value = str(word[4]).strip()
            x0 = float(word[0])

            if (
                value == str(row_number)
                and x0 <= 165
            ):
                serial_words.append(word)

        if serial_words:
            cells[serial_column].append(
                str(row_number)
            )

        # ------------------------------------------------------------
        # Build boundaries for columns after description.
        #
        # anchors currently begins at the description X position, so
        # anchors[1] may be a wrapped description word. Skip anchors
        # that are inside the description region and retain anchors
        # beginning with the first numeric column.
        # ------------------------------------------------------------

        logical_numeric_anchors = [
            x
            for x in anchors
            if x >= first_numeric_x - 2.0
        ]

        required_numeric_columns = column_count - 2

        if (
            len(logical_numeric_anchors)
            < required_numeric_columns
        ):
            # If the detected geometry doesn't expose enough numeric
            # anchors, retain the rightmost anchors. This avoids
            # promoting wrapped description words to columns.
            logical_numeric_anchors = anchors[
                -required_numeric_columns:
            ]

        # Construct boundaries between numeric columns.
        numeric_boundaries = []

        for i in range(
            len(logical_numeric_anchors) - 1
        ):
            numeric_boundaries.append(
                (
                    logical_numeric_anchors[i]
                    + logical_numeric_anchors[i + 1]
                )
                / 2.0
            )

        # ------------------------------------------------------------
        # Assign every source word.
        # ------------------------------------------------------------

        for word in sorted(
            row_words,
            key=lambda item: (
                float(item[1]),
                float(item[0]),
            ),
        ):

            x0 = float(word[0])
            value = str(word[4]).strip()

            if not value:
                continue

            # Serial number belongs explicitly to column 0.
            if (
                value == str(row_number)
                and x0 <= 165
            ):
                continue

            # Everything between the description start and the first
            # numeric column belongs to the description, regardless of
            # vertical wrapping.
            if (
                x0 >= description_x - 5
                and x0 < first_numeric_x - 5
            ):
                cells[
                    description_column
                ].append(value)
                continue

            # Words at/after the first numeric anchor are assigned to
            # the remaining logical columns.
            if x0 >= first_numeric_x - 5:

                numeric_column = 0

                while (
                    numeric_column
                    < len(numeric_boundaries)
                    and x0 >= numeric_boundaries[
                        numeric_column
                    ]
                ):
                    numeric_column += 1

                target_column = (
                    2 + numeric_column
                )

                if target_column >= column_count:
                    target_column = (
                        column_count - 1
                    )

                cells[
                    target_column
                ].append(value)

        row = [
            " ".join(cell).strip()
            for cell in cells
        ]

        # Verify the source row number.
        if not row[serial_column]:
            row[serial_column] = str(row_number)

        if not any(
            value
            for value in row
        ):
            return None

        return row

    # ================================================================
    # ROW NUMBER HELPERS
    # ================================================================

    def _extract_row_numbers(
        self,
        rows: list[list[str]],
    ) -> list[int]:

        numbers = []

        for row in rows:

            number = self._row_number(
                row
            )

            if number is not None:
                numbers.append(
                    number
                )

        return numbers

    def _row_number(
        self,
        row: list[str],
    ) -> int | None:

        for cell in row[:3]:

            value = str(
                cell or ""
            ).strip()

            match = re.fullmatch(
                r"([1-9][0-9]?)",
                value,
            )

            if match:
                return int(
                    match.group(1)
                )

        return None

    # ================================================================
    # WORD EXTRACTION
    # ================================================================

    def _get_words(
        self,
        page: Any,
    ) -> list[tuple]:

        try:
            return list(
                page.get_text(
                    "words"
                )
                or []
            )
        except Exception:
            return []

    # ================================================================
    # NORMALIZATION
    # ================================================================

    def _normalize_matrix(
        self,
        data: Any,
    ) -> list[list[str]]:

        if not isinstance(
            data,
            (list, tuple),
        ):
            return []

        output = []

        for row in data:

            if not isinstance(
                row,
                (list, tuple),
            ):
                row = [row]

            output.append(
                [
                    self._normalize_cell(
                        value
                    )
                    for value in row
                ]
            )

        output = [
            row
            for row in output
            if any(
                value != ""
                for value in row
            )
        ]

        if not output:
            return []

        width = max(
            len(row)
            for row in output
        )

        normalized = []

        for row in output:

            values = list(
                row
            )

            if len(values) < width:
                values.extend(
                    [""] * (
                        width
                        - len(values)
                    )
                )

            elif len(values) > width:
                values = values[
                    :width
                ]

            normalized.append(
                values
            )

        return normalized

    @staticmethod
    def _normalize_cell(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        text = str(
            value
        )

        text = text.replace(
            "\r\n",
            "\n",
        )

        text = text.replace(
            "\r",
            "\n",
        )

        return "\n".join(
            line.strip()
            for line in text.split(
                "\n"
            )
            if line.strip()
        ).strip()

    # ================================================================
    # BBOX
    # ================================================================

    @staticmethod
    def _extract_bbox(
        table: Any,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ] | None:

        bbox = getattr(
            table,
            "bbox",
            None,
        )

        if bbox is None:
            bbox = getattr(
                table,
                "rect",
                None,
            )

        if bbox is None:
            return None

        try:

            if hasattr(
                bbox,
                "x0",
            ):
                return (
                    float(bbox.x0),
                    float(bbox.y0),
                    float(bbox.x1),
                    float(bbox.y1),
                )

            if isinstance(
                bbox,
                (list, tuple),
            ) and len(bbox) >= 4:

                return (
                    float(bbox[0]),
                    float(bbox[1]),
                    float(bbox[2]),
                    float(bbox[3]),
                )

        except (
            TypeError,
            ValueError,
        ):
            return None

        return None
