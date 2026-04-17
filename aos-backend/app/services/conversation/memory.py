"""
AOS Conversation Memory — short-term (session window) + episodic references.

Short-term memory is the last-N messages of the active session, used to
build LLM context. Episodic memory (semantic search, pgvector) is a later
enhancement; stubs are in place.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationMessage, ConversationSession


class ConversationMemory:
    """Fetches short-term memory (message window) for an agent turn."""

    def __init__(self, session: AsyncSession, window: int = 20) -> None:
        self.session = session
        self.window = window

    async def get_history(
        self,
        conversation_id: uuid.UUID,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Return last-N messages in chronological order."""
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.session_id == conversation_id)
            .order_by(desc(ConversationMessage.created_at))
            .limit(limit or self.window)
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return [
            {
                "role": m.role,
                "content": m.content,
                "agent": m.agent,
                "intent": m.intent,
            }
            for m in rows
        ]

    async def get_session(self, conversation_id: uuid.UUID) -> Optional[ConversationSession]:
        return await self.session.get(ConversationSession, conversation_id)
