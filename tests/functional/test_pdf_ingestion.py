from pathlib import Path

from townplanning.modules.regulations.ingestion.ingestion_service import (
    IngestionService,
)

PDF = Path(
    "data/regulations/UDCPR.pdf"
)


def test_pdf_ingestion():

    service = IngestionService()

    results = service.ingest_pdf(

        pdf_path=str(PDF),

        start_page=45,

        end_page=511,
    )

    assert len(results) > 0