from __future__ import annotations

from townplanning.modules.memory.domain.conversation import (
    Conversation,
)
from townplanning.modules.memory.domain.message import (
    Message,
)
from townplanning.modules.memory.repositories.postgres_memory_repository import (
    PostgresMemoryRepository,
)


class MemoryService:
    """
    High-level conversation memory service.

    Responsibilities
    ----------------
    - Create conversations
    - Load conversation history
    - Store user messages
    - Store assistant messages

    Business logic belongs here.
    Database logic belongs in the repository.
    """

    def __init__(
        self,
        repository: PostgresMemoryRepository,
    ) -> None:

        self.repository = repository

    ####################################################################
    # Conversation
    ####################################################################

    def create_conversation(
        self,
    ) -> Conversation:

        return self.repository.create_conversation()

    def get_conversation(
        self,
        conversation_id: str,
    ) -> Conversation | None:

        return self.repository.get_conversation(
            conversation_id,
        )

    ####################################################################
    # History
    ####################################################################

    def load_history(
        self,
        conversation_id: str,
    ) -> list[Message]:

        return self.repository.load_messages(
            conversation_id,
        )

    ####################################################################
    # Save User Message
    ####################################################################

    def save_user_message(
        self,
        conversation_id: str,
        message: str,
        token_count: int = 0,
    ) -> Message:

        return self.repository.save_message(
            conversation_id=conversation_id,
            role="user",
            message=message,
            token_count=token_count,
        )

    ####################################################################
    # Save Assistant Message
    ####################################################################

    def save_assistant_message(
        self,
        conversation_id: str,
        message: str,
        token_count: int = 0,
    ) -> Message:

        return self.repository.save_message(
            conversation_id=conversation_id,
            role="assistant",
            message=message,
            token_count=token_count,
        )

    ####################################################################
    # Delete Conversation
    ####################################################################

    def delete_conversation(
        self,
        conversation_id: str,
    ) -> None:

        self.repository.delete_conversation(
            conversation_id,
        )

    ####################################################################
    # Helpers
    ####################################################################

    def conversation_exists(
        self,
        conversation_id: str,
    ) -> bool:

        return (
            self.repository.get_conversation(
                conversation_id,
            )
            is not None
        )

    def get_or_create_conversation(
        self,
        conversation_id: str | None,
    ) -> Conversation:

        if conversation_id is None:

            return self.create_conversation()

        conversation = self.get_conversation(
            conversation_id,
        )

        if conversation is None:

            return self.create_conversation()

        return conversation

    def append_interaction(
        self,
        conversation_id: str,
        question: str,
        answer: str,
    ) -> None:
        """
        Save one complete question/answer interaction.
        """

        self.save_user_message(
            conversation_id=conversation_id,
            message=question,
        )

        self.save_assistant_message(
            conversation_id=conversation_id,
            message=answer,
        )