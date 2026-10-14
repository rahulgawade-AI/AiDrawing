"""
Integration test for Full PDF ingestion.
"""

import logging
import traceback
from pathlib import Path

from townplanning.infrastructure.database.session import SessionLocal

from townplanning.modules.regulations.ingestion.pdf_reader import PDFReader
from townplanning.modules.regulations.ingestion.table_extractor import TableExtractor
from townplanning.modules.regulations.ingestion.document_analyzer import DocumentAnalyzer
from townplanning.modules.regulations.ingestion.page_filter import PageFilter
from townplanning.modules.regulations.ingestion.knowledge_extractor import KnowledgeExtractor
from townplanning.modules.regulations.ingestion.rule_extractor import RuleExtractor
from townplanning.modules.regulations.ingestion.full_pdf_ingestion import (
    FullPDFIngestionService,
)
from townplanning.modules.regulations.persistence.persistence_service import (
    PersistenceService,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main():

    pdf_path = Path(
        "data/regulations/UDCPR.pdf"
    )

    session = SessionLocal()

    try:

        service = FullPDFIngestionService(

            pdf_reader=PDFReader(),

            document_analyzer=DocumentAnalyzer(),

            page_filter=PageFilter(),

            knowledge_extractor=KnowledgeExtractor(),

            rule_extractor=RuleExtractor(),

            persistence_service=PersistenceService(session),

            table_extractor=TableExtractor(),

        )

        print("=" * 80)
        print("FULL PDF INGESTION TEST")
        print("=" * 80)

        service.ingest_pdf(

            pdf_path=pdf_path,

            start_page=417,

            #end_page=129,

        )

        print()
        print("=" * 80)
        print("SUCCESS")
        print("=" * 80)

    except Exception:

        print()
        print("=" * 80)
        print("PIPELINE FAILED")
        print("=" * 80)

        traceback.print_exc()

    finally:

        session.close()


if __name__ == "__main__":
    main()