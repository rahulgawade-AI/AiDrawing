"""
Knowledge Card Repository.
"""

from sqlalchemy.orm import Session

from townplanning.infrastructure.database.mappers.knowledge_mapper import (
    KnowledgeMapper,
)

from townplanning.infrastructure.database.models import (
    KnowledgeCardModel,
)

from townplanning.modules.regulations.domain import (
    KnowledgeCard,
)


class SQLAlchemyKnowledgeRepository:

    def __init__(
        self,
        session: Session,
    ):

        self.session = session

    # ---------------------------------------------------------

    def save(
        self,
        card: KnowledgeCard,
    ) -> None:

        model = KnowledgeMapper.to_model(
            card
        )

        self.session.merge(model)

        #self.session.commit()

    # ---------------------------------------------------------

    def get(
        self,
        card_id: str,
    ) -> KnowledgeCard | None:

        model = self.session.get(
            KnowledgeCardModel,
            card_id,
        )

        if model is None:

            return None

        return KnowledgeMapper.to_domain(
            model
        )

    # ---------------------------------------------------------

    def exists(
        self,
        card_id: str,
    ) -> bool:

        return (
            self.session.get(
                KnowledgeCardModel,
                card_id,
            )
            is not None
        )

    # ---------------------------------------------------------

    def delete(
        self,
        card_id: str,
    ):

        model = self.session.get(
            KnowledgeCardModel,
            card_id,
        )

        if model:

            self.session.delete(model)

            #self.session.commit()

    # ---------------------------------------------------------

    def list(self):

        models = self.session.query(
            KnowledgeCardModel
        ).all()

        return [

            KnowledgeMapper.to_domain(m)

            for m in models

        ]

   