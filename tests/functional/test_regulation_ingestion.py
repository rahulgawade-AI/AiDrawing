from pathlib import Path

from townplanning.modules.regulations.ingestion.ingestion_service import (
    IngestionService,
)


PDF = Path(
    "data/regulations/UDCPR.pdf"
)


def test_regulation_ingestion():

    service = IngestionService()

    result = service.ingest(

        pdf_path=str(PDF),

        page_number=85,
    )

    regulation = result["regulation"]

    knowledge = result["knowledge"]

    rules = result["rules"]

    # ------------------------------

    assert regulation.number != ""

    assert regulation.title != ""

    assert knowledge.title != ""

    assert knowledge.summary != ""

    assert isinstance(rules, list)

    assert len(rules) > 0
    assert hasattr(
    knowledge,
    "measurements",
)