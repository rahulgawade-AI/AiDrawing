"""
Persists extracted regulations, knowledge, rules and tables
into the database.
"""

from sqlalchemy.orm import Session

from townplanning.infrastructure.database.repositories import (
    SQLAlchemyKnowledgeRepository,
    SQLAlchemyRegulationRepository,
    SQLAlchemyRuleRepository,
    SQLAlchemyTableRepository,
)


class PersistenceService:

    def __init__(
        self,
        session: Session,
    ):

        self.session = session

        self.regulation_repository = (
            SQLAlchemyRegulationRepository(session)
        )

        self.knowledge_repository = (
            SQLAlchemyKnowledgeRepository(session)
        )

        self.rule_repository = (
            SQLAlchemyRuleRepository(session)
        )

        self.table_repository = (
            SQLAlchemyTableRepository(session)
        )

    # ---------------------------------------------------------
    # Persist complete regulation
    # ---------------------------------------------------------

    def persist(
        self,
        regulation,
        knowledge,
        rules,
        tables=None,
    ):

        try:

            # -----------------------------------------
            # Save Regulation
            # -----------------------------------------

            self.regulation_repository.save(
                regulation
            )

            # Flush parent so FK exists
            self.session.flush()

            # -----------------------------------------
            # Save Knowledge Card
            # -----------------------------------------

            self.knowledge_repository.save(
                knowledge
            )

            self.session.flush()

            # -----------------------------------------
            # Save Rules
            # -----------------------------------------

            for rule in rules or []:

                self.rule_repository.save(
                    rule
                )

            # -----------------------------------------
            # Save Tables
            # -----------------------------------------

            if tables:

                self.table_repository.save_many(
                    tables,
                    regulation.id,
                )

                # Ensure table records are written
                self.session.flush()

            # -----------------------------------------
            # Commit everything
            # -----------------------------------------

            self.session.commit()

            return {

                "regulation": regulation,

                "knowledge": knowledge,

                "rules": rules,

                "tables": tables or [],
            }

        except Exception as exc:

            self.session.rollback()

            raise exc

    # ---------------------------------------------------------
    # Persist tables only
    # ---------------------------------------------------------

    def persist_tables(
        self,
        tables,
        regulation_id: str,
    ):

        if not tables:

            return []

        try:

            self.table_repository.save_many(
                tables,
                regulation_id,
            )

            self.session.commit()

            return tables

        except Exception as exc:

            self.session.rollback()

            raise exc

    # ---------------------------------------------------------
    # Existing table lookup
    # ---------------------------------------------------------

    def get_tables_by_page(
        self,
        page_number: int,
    ):

        return self.table_repository.list_by_page(
            page_number
        )

    # ---------------------------------------------------------
    # Rollback
    # ---------------------------------------------------------

    def rollback(self):

        self.session.rollback()

    # ---------------------------------------------------------
    # Close
    # ---------------------------------------------------------

    def close(self):

        self.session.close()