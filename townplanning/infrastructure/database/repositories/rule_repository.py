"""
SQLAlchemy Rule Repository.
"""

from sqlalchemy import select

from townplanning.infrastructure.database.mappers import RuleMapper
from townplanning.infrastructure.database.models import RuleModel


class SQLAlchemyRuleRepository:

    def __init__(
        self,
        session,
    ):

        self.session = session

    # ---------------------------------------------------------

    def save(
        self,
        rule,
    ):

        model = RuleMapper.to_model(
            rule
        )

        self.session.merge(
            model
        )

        #self.session.commit()

        return rule

    # ---------------------------------------------------------

    def get(
        self,
        rule_id,
    ):

        model = self.session.get(
            RuleModel,
            rule_id,
        )

        if model is None:

            return None

        return RuleMapper.to_domain(
            model
        )

    # ---------------------------------------------------------

    def list(self):

        stmt = select(
            RuleModel
        )

        return [

            RuleMapper.to_domain(
                model
            )

            for model in self.session.scalars(
                stmt
            )

        ]

    # ---------------------------------------------------------

    def list_by_regulation(
        self,
        regulation_id,
    ):

        stmt = (

            select(
                RuleModel
            )

            .where(
                RuleModel.regulation_id
                == regulation_id
            )

        )

        return [

            RuleMapper.to_domain(
                model
            )

            for model in self.session.scalars(
                stmt
            )

        ]

    # ---------------------------------------------------------

    def exists(
        self,
        rule_id,
    ):

        return (

            self.session.get(
                RuleModel,
                rule_id,
            )

            is not None

        )

    # ---------------------------------------------------------

    def delete(
        self,
        rule_id,
    ):

        model = self.session.get(
            RuleModel,
            rule_id,
        )

        if model:

            self.session.delete(
                model
            )

            #self.session.commit()

   