"""
SQLAlchemy Table Repository.
"""

from sqlalchemy import select

from townplanning.infrastructure.database.mappers.table_mapper import (
    TableMapper,
)

from townplanning.infrastructure.database.models import (
    Table as TableModel,
)


class SQLAlchemyTableRepository:

    def __init__(
        self,
        session,
    ):
        self.session = session

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------

    def save(
        self,
        table,
        regulation_id: str,
    ):

        existing = self.get_by_page_and_index(
            regulation_id=regulation_id,
            page=table.page,
            table_index=table.index,
        )

        if existing is not None:

            return existing

        model = TableMapper.to_model(
            table,
            regulation_id,
        )

        self.session.merge(
            model
        )

        return table

    # ---------------------------------------------------------
    # Save many
    # ---------------------------------------------------------

    def save_many(
        self,
        tables,
        regulation_id: str,
    ):

        results = []

        for table in tables:

            results.append(
                self.save(
                    table,
                    regulation_id,
                )
            )

        return results

    # ---------------------------------------------------------
    # Get by ID
    # ---------------------------------------------------------

    def get(
        self,
        table_id: str,
    ):

        model = self.session.get(
            TableModel,
            table_id,
        )

        if model is None:

            return None

        return TableMapper.to_domain(
            model
        )

    # ---------------------------------------------------------
    # Exists
    # ---------------------------------------------------------

    def exists(
        self,
        table_id: str,
    ):

        return (
            self.session.get(
                TableModel,
                table_id,
            )
            is not None
        )

    # ---------------------------------------------------------
    # List all
    # ---------------------------------------------------------

    def list(self):

        stmt = select(
            TableModel
        )

        return [

            TableMapper.to_domain(
                model
            )

            for model in self.session.scalars(
                stmt
            )

        ]

    # ---------------------------------------------------------
    # List by regulation
    # ---------------------------------------------------------

    def list_by_regulation(
        self,
        regulation_id: str,
    ):

        stmt = (

            select(
                TableModel
            )

            .where(
                TableModel.regulation_id
                == regulation_id
            )

            .order_by(
                TableModel.page_number,
                TableModel.table_index,
            )

        )

        return [

            TableMapper.to_domain(
                model
            )

            for model in self.session.scalars(
                stmt
            )

        ]

    # ---------------------------------------------------------
    # List by page
    # ---------------------------------------------------------

    def list_by_page(
        self,
        page: int,
    ):

        stmt = (

            select(
                TableModel
            )

            .where(
                TableModel.page_number
                == page
            )

            .order_by(
                TableModel.table_index
            )

        )

        return [

            TableMapper.to_domain(
                model
            )

            for model in self.session.scalars(
                stmt
            )

        ]

    # ---------------------------------------------------------
    # Get by regulation + page + table index
    # ---------------------------------------------------------

    def get_by_page_and_index(
        self,
        regulation_id: str,
        page: int,
        table_index: int,
    ):

        stmt = (

            select(
                TableModel
            )

            .where(
                TableModel.regulation_id
                == regulation_id
            )

            .where(
                TableModel.page_number
                == page
            )

            .where(
                TableModel.table_index
                == table_index
            )

        )

        model = self.session.scalar(
            stmt
        )

        if model is None:

            return None

        return TableMapper.to_domain(
            model
        )

    # ---------------------------------------------------------
    # Delete
    # ---------------------------------------------------------

    def delete(
        self,
        table_id: str,
    ):

        model = self.session.get(
            TableModel,
            table_id,
        )

        if model:

            self.session.delete(
                model
            )