from pathlib import Path

from townplanning.modules.regulations.ingestion.ingestion_service import (
    IngestionService,
)

from townplanning.validation import (
    RegulationValidator,
)


PDF = Path(
    "data/regulations/UDCPR.pdf"
)


def test_validation():

    service = IngestionService()

    result = service.ingest(

        pdf_path=str(PDF),

        page_number=85,
    )

    validator = RegulationValidator()

    validation = validator.validate(

        result["regulation"],

        result["knowledge"],

        result["rules"],
    )

    assert validation.passed

    assert validation.error_count == 0

    assert validation.statistics["rules"] > 0