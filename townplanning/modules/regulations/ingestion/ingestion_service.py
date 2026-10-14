"""
Regulation Ingestion Service.

Coordinates the complete regulation ingestion pipeline.

Pipeline:

PDF
 ↓
PDFReader
 ↓
PageWindowBuilder
 ↓
TableExtractor
 ↓
DocumentAnalyzer
 ↓
RegulationChunk
 ↓
RegulationAssembler
 ↓
RegulationDocument
 ↓
KnowledgeExtractor
 ↓
RuleExtractor
 ↓
PersistenceService
"""

from __future__ import annotations

import time

from townplanning.modules.regulations.ingestion.pdf_reader import (
    PDFReader,
)

from townplanning.modules.regulations.ingestion.page_window import (
    PageWindowBuilder,
)

from townplanning.modules.regulations.ingestion.document_analyzer import (
    DocumentAnalyzer,
)

from townplanning.modules.regulations.ingestion.table_extractor import (
    TableExtractor,
)

from townplanning.modules.regulations.ingestion.page_filter import (
    PageFilter,
)

from townplanning.modules.regulations.ingestion.knowledge_extractor import (
    KnowledgeExtractor,
)

from townplanning.modules.regulations.ingestion.rule_extractor import (
    RuleExtractor,
)

from townplanning.modules.regulations.ingestion.regulation_chunk import (
    RegulationChunk,
)

from townplanning.modules.regulations.ingestion.regulation_assembler import (
    RegulationAssembler,
)

from townplanning.infrastructure.database.session import (
    SessionLocal,
)

from townplanning.modules.regulations.persistence import (
    PersistenceService,
)


class IngestionService:
    """
    Complete PDF regulation ingestion service.

    Important design rule:

    RegulationDocument is the canonical source object.

    The same RegulationDocument is passed to:

        KnowledgeExtractor
        RuleExtractor

    This guarantees that:

        regulation.id
        regulation.number
        regulation.chapter
        regulation.pages
        regulation.text
        regulation.tables

    remain consistent across the entire ingestion pipeline.
    """

    def __init__(self):

        self.reader = PDFReader()

        self.analyzer = DocumentAnalyzer()

        self.knowledge_extractor = (
            KnowledgeExtractor()
        )

        self.rule_extractor = (
            RuleExtractor()
        )

        self.page_filter = PageFilter()

    # ==========================================================
    # SINGLE PAGE
    # ==========================================================

    def ingest(
        self,
        pdf_path: str,
        page_number: int,
    ):
        """
        Process one PDF page.

        This method performs extraction only.

        Persistence is handled by ingest_pdf().
        """

        self.reader.open(pdf_path)

        try:

            # --------------------------------------------------
            # BUILD PAGE WINDOW
            # --------------------------------------------------

            builder = PageWindowBuilder(
                self.reader
            )

            window = builder.build(
                page_number
            )

            # --------------------------------------------------
            # PAGE FILTER
            # --------------------------------------------------

            should_process, reason = (
                self.page_filter.should_process(
                    page_number,
                    window.current_text,
                )
            )

            if not should_process:
                raise RuntimeError(reason)

            # --------------------------------------------------
            # TABLE EXTRACTION
            # --------------------------------------------------

            table_extractor = TableExtractor()

            tables = table_extractor.extract(
                self.reader,
                page_number,
            )

            window.tables = tables

            # --------------------------------------------------
            # DOCUMENT ANALYSIS
            # --------------------------------------------------

            analysis = self.analyzer.analyze(
                window
            )

            print(
                f"Page Type : {analysis.page_type}"
            )

            print(
                f"Chapter   : "
                f"{analysis.chapter_number}"
            )

            print(
                f"Headings  : "
                f"{len(analysis.regulations)}"
            )

            # --------------------------------------------------
            # PAGE TYPES THAT ARE NOT REGULATIONS
            # --------------------------------------------------

            SKIP_PAGE_TYPES = {
                "cover",
                "notification",
                "preface",
                "table_of_contents",
                "index",
                "definition",
                "appendix",
                "schedule",
                "form",
                "drawing",
                "blank",
                "other",
            }

            page_type = (
                analysis.page_type
                .lower()
                .strip()
            )

            if page_type in SKIP_PAGE_TYPES:

                raise RuntimeError(
                    f"Skipped ({page_type})"
                )

            # --------------------------------------------------
            # REQUIRE REGULATION HEADING
            # --------------------------------------------------

            if not analysis.regulations:

                raise RuntimeError(
                    "No regulation detected on page."
                )

            # --------------------------------------------------
            # CURRENT HEADING
            # --------------------------------------------------

            heading = (
                analysis.regulations[0]
            )

            # --------------------------------------------------
            # BUILD REGULATION CHUNK
            #
            # RegulationAssembler is responsible for creating
            # the canonical RegulationDocument.
            # --------------------------------------------------

            chunk = RegulationChunk(

                number=heading.number,

                title=heading.title,

                chapter_number=(
                    analysis.chapter_number
                    or ""
                ),

                chapter_title=(
                    getattr(
                        analysis,
                        "chapter_title",
                        "",
                    )
                    or ""
                ),

                page=page_number,

                text=window.current_text,

                tables=tables,
            )

            # --------------------------------------------------
            # ASSEMBLE
            # --------------------------------------------------

            assembler = RegulationAssembler()

            regulation = (
                assembler.add_chunk(chunk)
            )

            # A single chunk will remain pending
            # until flush().

            if regulation is None:

                regulation = (
                    assembler.flush()
                )

            if regulation is None:

                raise RuntimeError(
                    "RegulationAssembler did not "
                    "produce a RegulationDocument."
                )

            # --------------------------------------------------
            # KNOWLEDGE EXTRACTION
            #
            # IMPORTANT:
            #
            # KnowledgeExtractor expects:
            #
            #     RegulationDocument
            #
            # NOT PageAnalysis + PageWindow.
            # --------------------------------------------------

            knowledge = (
                self.knowledge_extractor.extract(
                    regulation
                )
            )

            # --------------------------------------------------
            # RULE EXTRACTION
            #
            # IMPORTANT:
            #
            # RuleExtractor expects:
            #
            #     RegulationDocument
            #     KnowledgeCard
            # --------------------------------------------------

            rules = (
                self.rule_extractor.extract(
                    regulation,
                    knowledge,
                )
            )

            return {
                "regulation": regulation,
                "knowledge": knowledge,
                "rules": rules,
                "tables": tables,
            }

        finally:

            self.reader.close()

    # ==========================================================
    # COMPLETE PDF
    # ==========================================================

    def ingest_pdf(
        self,
        pdf_path: str,
        start_page: int = 1,
        end_page: int | None = None,
    ):
        """
        Ingest a complete PDF page-by-page.

        Each successfully extracted RegulationDocument
        is persisted together with its KnowledgeCard,
        Rules and Tables.
        """

        # ------------------------------------------------------
        # DETERMINE PAGE COUNT
        # ------------------------------------------------------

        self.reader.open(pdf_path)

        try:

            total_pages = (
                self.reader.page_count
            )

        finally:

            self.reader.close()

        if end_page is None:
            end_page = total_pages

        if start_page < 1:
            raise ValueError(
                "start_page must be >= 1"
            )

        if end_page > total_pages:
            raise ValueError(
                f"end_page {end_page} exceeds "
                f"PDF page count {total_pages}"
            )

        if start_page > end_page:
            raise ValueError(
                "start_page must not exceed "
                "end_page"
            )

        # ------------------------------------------------------
        # DATABASE
        # ------------------------------------------------------

        session = SessionLocal()

        persistence = (
            PersistenceService(session)
        )

        results = []

        processed = 0
        skipped = 0
        failed = 0

        print()

        print("=" * 80)
        print("STARTING PDF INGESTION")
        print("=" * 80)

        print(
            f"PDF    : {pdf_path}"
        )

        print(
            f"Pages  : "
            f"{start_page} -> {end_page}"
        )

        print()

        try:

            for page_number in range(
                start_page,
                end_page + 1,
            ):

                start_time = time.time()

                print()
                print("=" * 80)
                print(
                    f"START PAGE {page_number}"
                )
                print("=" * 80)

                try:

                    result = self.ingest(
                        pdf_path=pdf_path,
                        page_number=page_number,
                    )

                    regulation = (
                        result["regulation"]
                    )

                    knowledge = (
                        result["knowledge"]
                    )

                    rules = (
                        result["rules"]
                    )

                    tables = (
                        result.get(
                            "tables",
                            [],
                        )
                    )

                    # --------------------------------------------------
                    # PERSIST
                    # --------------------------------------------------

                    persistence.persist(
                        regulation=regulation,
                        knowledge=knowledge,
                        rules=rules,
                        tables=tables,
                    )

                    elapsed = (
                        time.time()
                        - start_time
                    )

                    print()
                    print(
                        f"✓ Page "
                        f"{page_number} completed"
                    )

                    print(
                        f"Time       : "
                        f"{elapsed:.1f} sec"
                    )

                    print(
                        f"Regulation : "
                        f"{regulation.number}"
                    )

                    print(
                        f"Title      : "
                        f"{regulation.title}"
                    )

                    print(
                        f"Rules      : "
                        f"{len(rules)}"
                    )

                    print(
                        f"Tables     : "
                        f"{len(tables)}"
                    )

                    print(
                        "✓ PostgreSQL persistence complete"
                    )

                    results.append(
                        result
                    )

                    processed += 1

                except Exception as exc:

                    message = str(exc)

                    # --------------------------------------------------
                    # EXPECTED SKIPS
                    # --------------------------------------------------

                    expected_skips = {
                        "Blank page",
                        "Table of Contents",
                        "Too little text",
                        "No regulation detected on page.",
                    }

                    if (
                        message.startswith(
                            "Skipped ("
                        )
                        or message in expected_skips
                    ):

                        skipped += 1

                        print(
                            f"⚠ Page "
                            f"{page_number} skipped"
                        )

                        print(
                            f"Reason : {exc}"
                        )

                    else:

                        failed += 1

                        print()
                        print(
                            "!" * 80
                        )

                        print(
                            f"FAILED PAGE "
                            f"{page_number}"
                        )

                        print(
                            f"Reason : {exc}"
                        )

                        print(
                            "!" * 80
                        )

                        # --------------------------------------------------
                        # Continue with next page.
                        # --------------------------------------------------

                        import traceback

                        traceback.print_exc()

                    continue

            # ------------------------------------------------------
            # SUMMARY
            # ------------------------------------------------------

            print()
            print("=" * 80)
            print("INGESTION SUMMARY")
            print("=" * 80)

            print(
                f"Processed : {processed}"
            )

            print(
                f"Skipped   : {skipped}"
            )

            print(
                f"Failed    : {failed}"
            )

            print(
                f"Total     : "
                f"{end_page - start_page + 1}"
            )

            print("=" * 80)

            return results

        finally:

            persistence.close()

    # ==========================================================
    # TABLE INGESTION
    # ==========================================================

    def get_or_ingest_tables(
        self,
        pdf_path: str,
        page_number: int,
        regulation_id: str,
    ):
        """
        Get existing tables for a page.

        If none exist, extract them from the PDF
        and persist them against regulation_id.
        """

        session = SessionLocal()

        try:

            persistence = (
                PersistenceService(session)
            )

            # --------------------------------------------------
            # CHECK DATABASE
            # --------------------------------------------------

            existing_tables = (
                persistence.get_tables_by_page(
                    page_number
                )
            )

            if existing_tables:

                print(
                    f"Tables already exist for "
                    f"page {page_number}: "
                    f"{len(existing_tables)}"
                )

                return existing_tables

            # --------------------------------------------------
            # EXTRACT
            # --------------------------------------------------

            print(
                f"No tables found for page "
                f"{page_number}. "
                f"Running TableExtractor..."
            )

            self.reader.open(pdf_path)

            try:

                table_extractor = (
                    TableExtractor()
                )

                tables = (
                    table_extractor.extract(
                        self.reader,
                        page_number,
                    )
                )

            finally:

                self.reader.close()

            # --------------------------------------------------
            # NOTHING FOUND
            # --------------------------------------------------

            if not tables:

                print(
                    f"No tables extracted "
                    f"from page "
                    f"{page_number}"
                )

                return []

            print(
                f"Extracted {len(tables)} "
                f"table(s) from page "
                f"{page_number}"
            )

            # --------------------------------------------------
            # PERSIST
            # --------------------------------------------------

            persisted = (
                persistence.persist_tables(
                    tables,
                    regulation_id,
                )
            )

            print(
                f"Persisted {len(persisted)} "
                f"table(s) for page "
                f"{page_number}"
            )

            return persisted

        finally:

            session.close()