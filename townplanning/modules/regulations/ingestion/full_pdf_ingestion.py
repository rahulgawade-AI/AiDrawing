"""
Production Full PDF Ingestion Service.

Workflow

PDF
 ↓
PageWindowBuilder
 ↓
DocumentAnalyzer
 ↓
PageFilter
 ↓
RegulationSplitter
 ↓
RegulationAssembler
 ↓
KnowledgeExtractor
 ↓
RuleExtractor
 ↓
PersistenceService

This class contains NO extraction logic.
It only orchestrates the pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path

from townplanning.modules.regulations.ingestion.page_window import (
    PageWindowBuilder,
)
from townplanning.modules.regulations.ingestion.regulation_splitter import (
    RegulationSplitter,
)
from townplanning.modules.regulations.ingestion.regulation_assembler import (
    RegulationAssembler,
)
#from debug.debug_writer import DebugWriter



logger = logging.getLogger(__name__)


class FullPDFIngestionService:

    def __init__(
        self,
        pdf_reader,
        document_analyzer,
        page_filter,
        knowledge_extractor,
        rule_extractor,
        persistence_service,
        table_extractor,
    ):

        self.pdf_reader = pdf_reader
        self.document_analyzer = document_analyzer
        self.page_filter = page_filter

        self.knowledge_extractor = knowledge_extractor
        self.rule_extractor = rule_extractor
        self.persistence = persistence_service

        self.table_extractor = table_extractor

        self.window_builder = PageWindowBuilder(
                self.pdf_reader
            )

        self.splitter = RegulationSplitter()

        self.assembler = RegulationAssembler()

    # ------------------------------------------------------------

    def ingest_pdf(
        self,
        pdf_path: str | Path,
        start_page: int | None = None,
        end_page: int | None = None,
    ):

        pdf = self.pdf_reader.open(pdf_path)

        total_pages = pdf.page_count

        if start_page is None:
            start_page = 1

        if end_page is None:
            end_page = total_pages

        logger.info(
            "Processing pages %s - %s",
            start_page,
            end_page,
        )

        processed = 0
        skipped = 0
        failed = 0

        for page_number in range(start_page, end_page + 1):

            try:

                self._process_page(
                    pdf,
                    page_number,
                )

                processed += 1

            except SkipPage:

                skipped += 1

            except Exception:

                failed += 1

                logger.exception(
                    "Failed page %s",
                    page_number,
                )

        #
        # Flush last regulation
        #
        regulation = self.assembler.flush()

        if regulation:

            self._process_regulation(
                regulation
            )

        logger.info(
            "Completed PDF "
            "processed=%s "
            "skipped=%s "
            "failed=%s",
            processed,
            skipped,
            failed,
        )

    # ------------------------------------------------------------

    def _process_page(
        self,
        pdf,
        page_number,
    ):

        window = self.window_builder.build(
           # pdf,
            page_number,
        )

        window.tables = self.table_extractor.extract(
            pdf,
            page_number,
        )

        analysis = self.document_analyzer.analyze(
            window
        )

        #
        # Skip cover/index/etc.
        #
        if self.page_filter.should_skip(
            analysis
        ):

            raise SkipPage()

        chunks = self.splitter.split(
            analysis,
            window,
        )

        for chunk in chunks:

            completed = (
                self.assembler.add_chunk(
                    chunk
                )
            )

            if completed:

                self._process_regulation(
                    completed
                )

    # ------------------------------------------------------------

    def _process_regulation(
        self,
        regulation,
    ):

        logger.info(
            "Processing regulation %s",
            regulation.number,
        )

        knowledge = self.knowledge_extractor.extract(
            regulation
        )

        rules = self.rule_extractor.extract(
            regulation,
            knowledge,
        )

        self.persistence.persist(
            regulation=regulation,
            knowledge=knowledge,
            rules=rules,
        )


class SkipPage(Exception):
    """
    Internal control-flow exception for skipped pages.
    """