from pathlib import Path

from townplanning.infrastructure.database.session import (
    SessionLocal,
)

from townplanning.modules.regulations.ingestion.ingestion_service import (
    IngestionService,
)

from townplanning.modules.regulations.persistence import (
    PersistenceService,
)


PDF = Path(
    "data/regulations/UDCPR.pdf"
)


def test_persistence():

    session = SessionLocal()

    ingestion = IngestionService()

    persistence = PersistenceService(
        session
    )

    result = ingestion.ingest(

        pdf_path=str(PDF),

        page_number=85,
    )

    persistence.persist(

        regulation=result["regulation"],

        knowledge=result["knowledge"],

        rules=result["rules"],
    )

    session.close()