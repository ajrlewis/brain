import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cortex_state.models import Conversation, ConversationMessage


class StaleConversationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ConversationSnapshot:
    conversation: Conversation
    messages: tuple[ConversationMessage, ...]


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, owner_id: str) -> Conversation:
        conversation = Conversation(owner_id=owner_id)
        self._session.add(conversation)
        await self._session.flush()
        await self._session.refresh(conversation)
        return conversation

    async def list(self, owner_id: str, *, limit: int, offset: int) -> tuple[Conversation, ...]:
        rows = await self._session.scalars(
            select(Conversation)
            .where(Conversation.owner_id == owner_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return tuple(rows)

    async def get(self, owner_id: str, conversation_id: uuid.UUID) -> ConversationSnapshot | None:
        conversation = await self._session.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id, Conversation.owner_id == owner_id)
        )
        if conversation is None:
            return None
        return ConversationSnapshot(conversation, tuple(conversation.messages))

    async def append_turn(
        self,
        *,
        owner_id: str,
        conversation_id: uuid.UUID,
        observed_version: int,
        user_content: str,
        assistant_content: str,
    ) -> None:
        changed = await self._session.execute(
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.owner_id == owner_id,
                Conversation.version == observed_version,
            )
            .values(version=observed_version + 2, updated_at=datetime.now().astimezone())
        )
        if changed.rowcount != 1:  # type: ignore[attr-defined]
            raise StaleConversationError
        self._session.add_all(
            [
                ConversationMessage(
                    conversation_id=conversation_id,
                    sequence=observed_version + 1,
                    role="user",
                    content=user_content,
                ),
                ConversationMessage(
                    conversation_id=conversation_id,
                    sequence=observed_version + 2,
                    role="assistant",
                    content=assistant_content,
                ),
            ]
        )
        await self._session.flush()
