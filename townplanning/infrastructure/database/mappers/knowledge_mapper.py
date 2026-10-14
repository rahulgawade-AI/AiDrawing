"""
Maps between KnowledgeCard domain objects and SQLAlchemy models.
"""

from townplanning.modules.regulations.domain import KnowledgeCard

from townplanning.infrastructure.database.models import (
    KnowledgeCardModel,
)


class KnowledgeMapper:

    @staticmethod
    def to_model(
        card: KnowledgeCard,
    ) -> KnowledgeCardModel:

        return KnowledgeCardModel(

            id=card.id,

            regulation_id=card.regulation_id,

            title=card.title,

            summary=card.summary,

            purpose=card.purpose,

            scope=card.scope,

            definitions=card.definitions,

            permissions=card.permissions,

            conditions=card.conditions,

            prohibitions=card.prohibitions,

            measurements=card.measurements,

            exceptions=card.exceptions,

            applicability=card.applicability,

            authority=card.authority,

            inputs=card.inputs,

            outputs=card.outputs,

            references=card.references,

            related_regulations=card.related_regulations,

            keywords=card.keywords,

            examples=card.examples,

            notes=card.notes,

            extra_metadata=card.metadata,
        )

    # ---------------------------------------------------------

    @staticmethod
    def to_domain(
        model: KnowledgeCardModel,
    ) -> KnowledgeCard:

        return KnowledgeCard(

            id=model.id,

            regulation_id=model.regulation_id,

            title=model.title,

            summary=model.summary,

            purpose=model.purpose,

            scope=model.scope,

            definitions=model.definitions,

            permissions=model.permissions,

            conditions=model.conditions,

            prohibitions=model.prohibitions,

            measurements=model.measurements,

            exceptions=model.exceptions,

            applicability=model.applicability,

            authority=model.authority,

            inputs=model.inputs,

            outputs=model.outputs,

            references=model.references,

            related_regulations=model.related_regulations,

            keywords=model.keywords,

            examples=model.examples,

            notes=model.notes,

            metadata=model.extra_metadata,
        )