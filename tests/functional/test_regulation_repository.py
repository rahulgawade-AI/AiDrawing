from uuid import uuid4

from sqlalchemy import text

from townplanning.infrastructure.database import (
    Base,
    SessionLocal,
    engine,
)

from townplanning.infrastructure.database.repositories import (
    SQLAlchemyRegulationRepository,
)

from townplanning.modules.regulations.domain import (
    Regulation,
)


def test_regulation_repository_workflow():

    Base.metadata.create_all(engine)

    session = SessionLocal()

    repository = SQLAlchemyRegulationRepository(
        session
    )

    regulation = Regulation(

        id=str(uuid4()),

        number="5.1.1",

        chapter="5",

        title="Gaothan",

        text="Development permitted...",

        page_start=85,

        page_end=86,
    )

    repository.save(regulation)
    session.commit()

    loaded = repository.get(
        regulation.id
    )

    assert loaded is not None

    assert loaded.number == "5.1.1"

    assert loaded.title == "Gaothan"

    repository.delete(
        regulation.id
    )
    session.commit()
    deleted = repository.get(
        regulation.id
    )
    session.commit()
    assert deleted is None

    session.close()