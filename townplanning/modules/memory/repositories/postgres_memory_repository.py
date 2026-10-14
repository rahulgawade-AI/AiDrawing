from __future__ import annotations

from uuid import uuid4

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.modules.memory.models.conversation_model import (
    ConversationModel,
)
from townplanning.modules.memory.models.conversation_message_model import (
    ConversationMessageModel,
)
from townplanning.modules.memory.domain.conversation import Conversation
from townplanning.modules.memory.domain.message import Message


class PostgresMemoryRepository:
    """
    PostgreSQL repository for conversation memory.
    """

    ####################################################################
    # Conversation
    ####################################################################

    def create_conversation(self) -> Conversation:

        session = SessionLocal()

        try:

            model = ConversationModel()

            session.add(model)

            session.commit()

            session.refresh(model)

            return Conversation(
                id=str(model.id),
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

        finally:
            session.close()

    def get_conversation(
        self,
        conversation_id: str,
    ) -> Conversation | None:

        session = SessionLocal()

        try:

            model = (
                session.query(ConversationModel)
                .filter(
                    ConversationModel.id == conversation_id
                )
                .first()
            )

            if model is None:
                return None

            return Conversation(
                id=str(model.id),
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

        finally:
            session.close()

    ####################################################################
    # Messages
    ####################################################################

    def load_messages(
        self,
        conversation_id: str,
    ) -> list[Message]:

        session = SessionLocal()

        try:

            models = (
                session.query(
                    ConversationMessageModel
                )
                .filter(
                    ConversationMessageModel.conversation_id
                    == conversation_id
                )
                .order_by(
                    ConversationMessageModel.created_at.asc()
                )
                .all()
            )

            return [
                Message(
                    id=str(m.id),
                    conversation_id=str(
                        m.conversation_id
                    ),
                    role=m.role,
                    message=m.message,
                    created_at=m.created_at,
                    token_count=m.token_count,
                )
                for m in models
            ]

        finally:
            session.close()

    def save_message(
        self,
        conversation_id: str,
        role: str,
        message: str,
        token_count: int = 0,
    ) -> Message:

        session = SessionLocal()

        try:

            model = ConversationMessageModel(
                conversation_id=conversation_id,
                role=role,
                message=message,
                token_count=token_count,
            )

            session.add(model)

            session.commit()

            session.refresh(model)

            return Message(
                id=str(model.id),
                conversation_id=str(
                    model.conversation_id
                ),
                role=model.role,
                message=model.message,
                created_at=model.created_at,
                token_count=model.token_count,
            )

        finally:
            session.close()

    ####################################################################
    # Delete
    ####################################################################

    def delete_conversation(
        self,
        conversation_id: str,
    ) -> None:

        session = SessionLocal()

        try:

            session.query(
                ConversationModel
            ).filter(
                ConversationModel.id == conversation_id
            ).delete()

            session.commit()

        finally:
            session.close()