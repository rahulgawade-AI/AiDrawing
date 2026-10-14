"""
Persist all extractable tables from a UDCPR PDF.

This service reuses the existing:
    PDFReader
    TableExtractor
    SQLAlchemyRegulationRepository
    SQLAlchemyTableRepository

It does not create any new database infrastructure.

The operation is idempotent:
existing tables are detected by regulation + page + table index
through SQLAlchemyTableRepository.
"""

from __future__ import annotations

import logging
from pathlib import Path

from townplanning.infrastructure.database.repositories import (
    SQLAlchemyRegulationRepository,
    SQLAlchemyTableRepository,
)
from townplanning.infrastructure.database.session import SessionLocal
from townplanning.modules.regulations.ingestion.pdf_reader import PDFReader
from townplanning.modules.regulations.ingestion.table_extractor import (
    TableExtractor,
)


logger = logging.getLogger(__name__)


class TableExtractionService:

    def __init__(
        self,
        pdf_path: str,
    ):
        self.pdf_path = Path(pdf_path)

        if not self.pdf_path.exists():
            raise FileNotFoundError(
                f"UDCPR PDF not found: {self.pdf_path}"
            )

        self.reader = PDFReader().open(
            str(self.pdf_path)
        )

        self.extractor = TableExtractor()

        self.session = SessionLocal()

        self.regulation_repository = (
            SQLAlchemyRegulationRepository(
                self.session
            )
        )

        self.table_repository = (
            SQLAlchemyTableRepository(
                self.session
            )
        )
        self.regulations = (
            self.regulation_repository.list()
        )

        self.total_pages = self.reader.page_count

        self.pages_processed = 0
        self.pages_with_tables = 0

        self.tables_found = 0
        self.tables_saved = 0
        self.tables_existing = 0
        self.tables_skipped = 0
        self.tables_failed = 0

    # ==========================================================
    # CLOSE
    # ==========================================================

    def close(self):

        try:
            self.reader.close()
        finally:
            self.session.close()

    # ==========================================================
    # REGULATION LOOKUP
    # ==========================================================

    def _get_regulation_for_page(
        self,
        page_number: int,
    ):
        """
        Find the RegulationDocument covering the given PDF page.

        RegulationDocument uses:
            start_page
            end_page
        """

        regulations = self.regulation_repository.list()

        matches = []

        for regulation in regulations:

            start_page = getattr(
                regulation,
                "start_page",
                None,
            )

            end_page = getattr(
                regulation,
                "end_page",
                None,
            )

            if start_page is None:
                continue

            if end_page is None:
                end_page = start_page

            if (
                start_page
                <= page_number
                <= end_page
            ):
                matches.append(
                    regulation
                )

        if not matches:
            return None

        # Prefer the most specific regulation range.
        matches.sort(
            key=lambda item: (
                getattr(
                    item,
                    "end_page",
                    item.start_page,
                )
                - item.start_page
            )
        )

        return matches[0]

    # ==========================================================
    # TABLE EXISTENCE
    # ==========================================================

    def _existing_table(
        self,
        regulation_id: str,
        page_number: int,
        table_index: int,
    ):

        return self.table_repository.get_by_page_and_index(
            regulation_id=regulation_id,
            page=page_number,
            table_index=table_index,
        )

    # ==========================================================
    # TABLE QUALITY
    # ==========================================================

    @staticmethod
    def _is_real_table(table) -> bool:
        """
        Reject empty structures produced by PyMuPDF for
        section headings.

        A real table must contain either:
            - rows
            - or meaningful headers
        """

        rows = table.rows or []
        headers = table.headers or []

        if rows:
            return True

        meaningful_headers = [
            str(value).strip()
            for value in headers
            if str(value).strip()
        ]

        # A heading such as:
        # 8.2 OFF STREET PARKING REQUIREMENT
        # should not be persisted as a regulatory table.
        if len(meaningful_headers) <= 1:
            return False

        return False


    def _merge_continuation_table(self, table, regulation):
            """
            Merge Table 6-D continuation rows from PDF page 127 into the
            canonical Table 6-D record on page 126.

            Page 127 is physically extracted as a separate table, but rows
            5, 6 and 7 are continuations of the canonical Table 6-D.
            """

            if table.page != 127:
                return None

            continuation_rows = list(table.rows or [])

            if not continuation_rows:
                return None

            # ------------------------------------------------------------------
            # Locate canonical Table 6-D on page 126.
            # ------------------------------------------------------------------
            canonical = None

            for candidate in self.table_repository.list():
                if candidate.page != 126:
                    continue

                headers_text = " ".join(
                    str(value).strip()
                    for value in (candidate.headers or [])
                    if str(value).strip()
                ).lower()

                rows_text = " ".join(
                    str(value).strip()
                    for row in (candidate.rows or [])
                    for value in (row or [])
                    if str(value).strip()
                ).lower()

                combined_text = f"{headers_text} {rows_text}"

                if "table no.6-d" in combined_text:
                    canonical = candidate
                    break

            if canonical is None:
                return None

            # ------------------------------------------------------------------
            # Canonical Table 6-D physical-column mapping.
            # ------------------------------------------------------------------
            target_columns = {
                0: 1,    # serial
                1: 4,    # description
                2: 7,    # plot size
                3: 10,   # road width
                4: 13,   # front setback
                5: 16,   # side setback
                6: 19,   # rear setback
                7: 22,   # remarks
            }

            # ------------------------------------------------------------------
            # Existing serial numbers in canonical table.
            # ------------------------------------------------------------------
            existing_serials = set()

            for row in canonical.rows or []:
                if len(row) > 1:
                    serial = str(row[1]).strip()
                    if serial in {"1", "2", "3", "4", "5", "6", "7"}:
                        existing_serials.add(serial)

            # ------------------------------------------------------------------
            # Append missing continuation rows.
            # ------------------------------------------------------------------
            merged_count = 0

            for source_row in continuation_rows:
                if len(source_row) < 8:
                    continue

                serial = str(source_row[0]).strip()

                if serial not in {"5", "6", "7"}:
                    continue

                if serial in existing_serials:
                    continue

                target_row = [""] * len(canonical.headers)

                for source_index, target_index in target_columns.items():
                    if source_index < len(source_row):
                        target_row[target_index] = source_row[source_index]

                canonical.rows.append(target_row)
                existing_serials.add(serial)
                merged_count += 1

            # ------------------------------------------------------------------
            # Persist canonical Table 6-D.
            # ------------------------------------------------------------------
            if merged_count > 0:
                self.table_repository.save(
                    canonical,
                    regulation.id,
                )
                self.session.flush()

            # ------------------------------------------------------------------
            # Remove the physical page-127 duplicate if one exists.
            # ------------------------------------------------------------------
            duplicate = self._existing_table(
                regulation_id=regulation.id,
                page_number=127,
                table_index=table.index,
            )

            if duplicate is not None and duplicate.id != canonical.id:
                self.table_repository.delete(duplicate.id)
                self.session.flush()

            return canonical
    # ==========================================================
    # SAVE TABLE
    # ==========================================================

    def _save_table(self, table, regulation):
        # ---------------------------------------------------------
        # Continuation page handling
        # ---------------------------------------------------------
        merged = self._merge_continuation_table(
            table,
            regulation,
        )

        if merged is not None:
            self.tables_existing += 1

            # The continuation table is now represented by the
            # canonical Table 6-D record. Do not persist the physical
            # continuation as a separate logical table.
            return merged

        # ---------------------------------------------------------
        # Normal table persistence
        # ---------------------------------------------------------
        existing = self._existing_table(
            regulation_id=regulation.id,
            page_number=table.page,
            table_index=table.index,
        )

        if existing is not None:
            self.tables_existing += 1

            saved = self.table_repository.save(
                table,
                regulation.id,
            )

            self.session.flush()

            return saved

        self.table_repository.save(
            table,
            regulation.id,
        )

        self.session.flush()

        self.tables_saved += 1

        return table
    # ==========================================================
    # PROCESS PAGE
    # ==========================================================

    def process_page(
        self,
        page_number: int,
    ):

        tables = self.extractor.extract(
            self.reader,
            page_number,
        )

        self.pages_processed += 1

        if not tables:
            return []

        self.pages_with_tables += 1

        self.tables_found += len(tables)

        regulation = (
            self._get_regulation_for_page(
                page_number
            )
        )

        if regulation is None:

            self.tables_skipped += len(tables)

            logger.warning(
                "No regulation found for page %s; "
                "skipping %s extracted tables",
                page_number,
                len(tables),
            )

            return []

        saved = []

        for table in tables:

            try:

                if not self._is_real_table(
                    table
                ):
                    self.tables_skipped += 1

                    logger.debug(
                        "Skipping non-table structure "
                        "page=%s index=%s headers=%s",
                        table.page,
                        table.index,
                        table.headers,
                    )

                    continue

                result = self._save_table(
                    table,
                    regulation,
                )

                saved.append(result)

            except Exception:

                self.tables_failed += 1

                logger.exception(
                    "Failed to persist table "
                    "page=%s index=%s",
                    table.page,
                    table.index,
                )

        return saved

    # ==========================================================
    # EXTRACT ENTIRE PDF
    # ==========================================================

    def extract(
        self,
        start_page: int = 1,
        end_page: int | None = None,
        commit_interval: int = 25,
    ):

        if end_page is None:
            end_page = self.total_pages

        start_page = max(
            1,
            start_page,
        )

        end_page = min(
            self.total_pages,
            end_page,
        )

        logger.info(
            "Starting table persistence: pages %s-%s",
            start_page,
            end_page,
        )

        try:

            for page_number in range(
                start_page,
                end_page + 1,
            ):

                self.process_page(
                    page_number
                )

                if (
                    self.pages_processed
                    % commit_interval
                    == 0
                ):
                    self.session.commit()

                    logger.info(
                        "Progress: page=%s/%s "
                        "found=%s saved=%s existing=%s "
                        "skipped=%s failed=%s",
                        page_number,
                        end_page,
                        self.tables_found,
                        self.tables_saved,
                        self.tables_existing,
                        self.tables_skipped,
                        self.tables_failed,
                    )

            self.session.commit()

            return self.statistics()

        except Exception:

            self.session.rollback()

            logger.exception(
                "Table persistence failed"
            )

            raise

    # ==========================================================
    # STATISTICS
    # ==========================================================

    def statistics(self):

        return {
            "pdf": str(self.pdf_path),
            "total_pages": self.total_pages,
            "pages_processed": self.pages_processed,
            "pages_with_tables": self.pages_with_tables,
            "tables_found": self.tables_found,
            "tables_saved": self.tables_saved,
            "tables_existing": self.tables_existing,
            "tables_skipped": self.tables_skipped,
            "tables_failed": self.tables_failed,
        }


# ==============================================================
# CLI
# ==============================================================

def main():

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s "
            "%(message)s"
        ),
    )

    pdf_path = (
        "data/regulations/UDCPR.pdf"
    )

    service = TableExtractionService(
        pdf_path
    )

    try:

        result = service.extract()

        print()
        print("=" * 80)
        print("UDCPR TABLE PERSISTENCE COMPLETE")
        print("=" * 80)

        for key, value in result.items():
            print(
                f"{key:25}: {value}"
            )

    finally:

        service.close()


if __name__ == "__main__":
    main()
