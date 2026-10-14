"""
Resolve regulatory tables from the canonical PostgreSQL table store.

If a requested table is missing, discover it from the existing UDCPR PDF
using the existing PDFReader and TableExtractor, then persist it through
the existing TableRepository.
"""

from __future__ import annotations

from pathlib import Path

from townplanning.infrastructure.database.repositories import (
    SQLAlchemyRegulationRepository,
    SQLAlchemyTableRepository,
)
from townplanning.modules.regulations.ingestion.pdf_reader import PDFReader
from townplanning.modules.regulations.ingestion.table_extractor import (
    TableExtractor,
)


class RegulatoryTableResolver:

    def __init__(
        self,
        session,
        pdf_path: str,
    ):
        self.session = session
        self.pdf_path = Path(pdf_path)

        if not self.pdf_path.exists():
            raise FileNotFoundError(self.pdf_path)

        self.reader = None
        self.extractor = TableExtractor()

        self.table_repository = SQLAlchemyTableRepository(
            session
        )

        self.regulation_repository = (
            SQLAlchemyRegulationRepository(session)
        )

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def resolve(
        self,
        table_reference: str,
    ):
        """
        Return a canonical table.

        First searches PostgreSQL.

        If the table is missing, discovers it from the source PDF,
        persists it, and returns it.
        """

        table = self._find_existing(
            table_reference
        )

        if table is not None:
            return table

        return self._discover_and_persist(
            table_reference
        )

    # ---------------------------------------------------------
    # Existing database lookup
    # ---------------------------------------------------------

    def _find_existing(
        self,
        table_reference: str,
    ):
        reference = self._normalize(
            table_reference
        )

        tables = self.table_repository.list()

        for table in tables:

            candidates = []

            if table.title:
                candidates.append(table.title)

            if table.headers:
                candidates.extend(
                    str(header)
                    for header in table.headers
                    if header
                )

            for candidate in candidates:

                if self._normalize(candidate) == reference:
                    return table

                if reference in self._normalize(candidate):
                    return table

        return None

    # ---------------------------------------------------------
    # PDF discovery
    # ---------------------------------------------------------

    def _discover_and_persist(
        self,
        table_reference: str,
    ):

        self.reader = PDFReader().open(
            str(self.pdf_path)
        )

        try:

            for page_number in range(
                1,
                self.reader.page_count + 1,
            ):

                tables = self.extractor.extract(
                    self.reader,
                    page_number,
                )

                for table in tables:

                    if not self._matches(
                        table,
                        table_reference,
                    ):
                        continue

                    regulation = (
                        self.regulation_repository
                        .get_by_page(page_number)
                    )

                    if regulation is None:
                        continue

                    self.table_repository.save(
                        table,
                        regulation.id,
                    )

                    self.session.commit()

                    return self.table_repository.get(
                        table.id
                    )

            return None

        finally:

            self.reader.close()
            self.reader = None

    # ---------------------------------------------------------
    # Matching
    # ---------------------------------------------------------

    @staticmethod
    def _matches(
        table,
        table_reference: str,
    ) -> bool:

        reference = (
            RegulatoryTableResolver
            ._normalize(table_reference)
        )

        candidates = []

        if table.title:
            candidates.append(table.title)

        if table.headers:
            candidates.extend(
                str(header)
                for header in table.headers
                if header
            )

        for candidate in candidates:

            candidate_normalized = (
                RegulatoryTableResolver
                ._normalize(candidate)
            )

            if reference in candidate_normalized:
                return True

        return False

    # ---------------------------------------------------------
    # Normalization
    # ---------------------------------------------------------

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:

        return (
            str(value)
            .lower()
            .replace("-", "")
            .replace(" ", "")
            .replace(".", "")
            .replace(":", "")
            .strip()
        )
