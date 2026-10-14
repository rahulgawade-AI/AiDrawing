from sqlalchemy import select

from townplanning.infrastructure.database.mappers import RegulationMapper
from townplanning.infrastructure.database.models import RegulationModel

from townplanning.modules.regulations.repositories import RegulationRepository
from townplanning.modules.regulations.ingestion.regulation_document import (
    RegulationDocument,
)
from sqlalchemy import select, and_

class SQLAlchemyRegulationRepository(RegulationRepository):

    def __init__(self, session):
        self.session = session

    def save(
        self,
        regulation: RegulationDocument,
    ) -> RegulationDocument:

        model = RegulationMapper.to_model(regulation)

        self.session.merge(model)
        #self.session.commit()

        return regulation

    def get(
        self,
        regulation_id: str,
    ) -> RegulationDocument | None:

        model = self.session.get(
            RegulationModel,
            regulation_id,
        )

        if model is None:
            return None

        return RegulationMapper.to_domain(model)

    def get_by_number(
        self,
        number: str,
    ) -> RegulationDocument | None:

        stmt = (
            select(RegulationModel)
            .where(RegulationModel.number == number)
        )

        model = self.session.scalar(stmt)

        if model is None:
            return None

        return RegulationMapper.to_domain(model)

    def list(
        self,
    ) -> list[RegulationDocument]:

        stmt = select(RegulationModel)

        return [
            RegulationMapper.to_domain(model)
            for model in self.session.scalars(stmt)
        ]

    def delete(
        self,
        regulation_id: str,
    ) -> None:

        model = self.session.get(
            RegulationModel,
            regulation_id,
        )

        if model is not None:
            self.session.delete(model)
            #self.session.commit()

    ...

    def get_by_page(
        self,
        page: int,
    ) -> RegulationDocument | None:

        stmt = (
            select(RegulationModel)
            .where(
                and_(
                    RegulationModel.page_start <= page,
                    RegulationModel.page_end >= page,
                )
            )
        )

        model = self.session.scalar(stmt)

        if model is None:
            return None

        return RegulationMapper.to_domain(model)

 

   