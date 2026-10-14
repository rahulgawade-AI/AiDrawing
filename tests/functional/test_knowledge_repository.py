from uuid import uuid4

from townplanning.infrastructure.database.repositories import (
    SQLAlchemyKnowledgeRepository,
    SQLAlchemyRegulationRepository,
)

from townplanning.infrastructure.database.session import (
    SessionLocal,
)

from townplanning.modules.regulations.domain import (
    KnowledgeCard,
    Regulation,
)


def test_knowledge_repository():

    session = SessionLocal()

    regulation_repo = SQLAlchemyRegulationRepository(session)

    knowledge_repo = SQLAlchemyKnowledgeRepository(session)

    # ----------------------------------------------------------
    # Create parent Regulation
    # ----------------------------------------------------------

    regulation = Regulation(

        id=str(uuid4()),

        number="1.1",

        chapter="1",

        title="Test Regulation",

        text="Test regulation text",

        page_start=1,

        page_end=1,
    )

    regulation_repo.save(regulation)

    # ----------------------------------------------------------
    # Create Knowledge Card
    # ----------------------------------------------------------

    card = KnowledgeCard(

        id=str(uuid4()),

        regulation_id=regulation.id,

        title="FSI",

        summary="Summary",

        purpose="Purpose",
    )

    knowledge_repo.save(card)
    session.commit()

    # ----------------------------------------------------------
    # Verify
    # ----------------------------------------------------------

    loaded = knowledge_repo.get(card.id)

    assert loaded is not None

    assert loaded.id == card.id

    assert loaded.regulation_id == regulation.id

    assert loaded.title == "FSI"

    assert knowledge_repo.exists(card.id)

    # ----------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------

    knowledge_repo.delete(card.id)
    session.commit()

    regulation_repo.delete(regulation.id)
    session.commit()

    assert not knowledge_repo.exists(card.id)

    session.close()