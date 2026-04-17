"""
AOS Conversation Service — the top-level entry point for chat turns.

Flow:
  1. Ensure session (create or fetch).
  2. Persist user message.
  3. Classify intent (heuristics → LLM router).
  4. Ask orchestrator to run the matched domain agent.
  5. Persist assistant message with full trace (tool calls, tool results,
     approvals, timings, tokens).
  6. Publish domain event on Redis for downstream listeners.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, AgentResult
from app.agents.orchestrator import Orchestrator
from app.core.events import EventBus
from app.models.conversation import ConversationMessage, ConversationSession
from app.services.conversation.intent import IntentClassifier, IntentResult
from app.services.conversation.memory import ConversationMemory


class ConversationService:
    """High-level conversation orchestration."""

    def __init__(
        self,
        db: AsyncSession,
        orchestrator: Orchestrator,
        classifier: Optional[IntentClassifier] = None,
    ) -> None:
        self.db = db
        self.orchestrator = orchestrator
        self.classifier = classifier or IntentClassifier()
        self.memory = ConversationMemory(db)

    # ---- Session management ------------------------------------------------

    async def start_session(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        channel: str = "web",
        language: str = "en",
        title: Optional[str] = None,
    ) -> ConversationSession:
        sess = ConversationSession(
            org_id=org_id,
            user_id=user_id,
            channel=channel,
            language=language,
            title=title,
            status="active",
        )
        self.db.add(sess)
        await self.db.commit()
        await self.db.refresh(sess)
        return sess

    async def end_session(self, session_id: uuid.UUID) -> None:
        await self.db.execute(
            update(ConversationSession)
            .where(ConversationSession.id == session_id)
            .values(status="ended")
        )
        await self.db.commit()

    async def get_session(self, session_id: uuid.UUID) -> Optional[ConversationSession]:
        return await self.db.get(ConversationSession, session_id)

    # ---- Turn execution ----------------------------------------------------

    async def handle_turn(
        self,
        session_id: uuid.UUID,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        message: str,
        channel: str = "web",
        language: str = "en",
    ) -> dict[str, Any]:
        """Execute one user turn and return the assistant response payload."""
        sess = await self.get_session(session_id)
        if sess is None:
            raise ValueError(f"Session {session_id} not found")

        # 1. Persist user message
        user_msg = ConversationMessage(
            session_id=session_id,
            role="user",
            content=message,
        )
        self.db.add(user_msg)

        # 2. Build agent context with recent history
        history = await self.memory.get_history(session_id)
        ctx = AgentContext(
            org_id=org_id,
            user_id=user_id,
            user_role=user_role,
            session_id=session_id,
            channel=channel,
            language=language,
            history=history,
        )

        # 3. Classify intent
        intent: IntentResult = await self.classifier.classify(message, ctx)

        # If confidence too low and we have a clarifying question, return early
        if intent.confidence < 0.5 and intent.clarifying_question:
            assistant_msg = ConversationMessage(
                session_id=session_id,
                role="assistant",
                content=intent.clarifying_question,
                agent="router",
                intent=intent.intent,
                entities={"source": intent.source, "confidence": intent.confidence},
            )
            self.db.add(assistant_msg)
            await self._bump_session(sess, count=2)
            await self.db.commit()
            return {
                "response": intent.clarifying_question,
                "intent": intent.intent,
                "confidence": intent.confidence,
                "requires_clarification": True,
                "agent": "router",
            }

        # 4. Run the chosen agent via orchestrator
        agent_name = intent.agent_name or "router"
        try:
            result: AgentResult = await self.orchestrator.run(
                agent_name=agent_name,
                user_message=message,
                context=ctx,
                session=self.db,
            )
            result.intent = intent.intent
        except Exception as exc:
            assistant_msg = ConversationMessage(
                session_id=session_id,
                role="assistant",
                content=f"Sorry, something went wrong: {exc}",
                agent=agent_name,
                intent=intent.intent,
                error=str(exc),
            )
            self.db.add(assistant_msg)
            await self._bump_session(sess, count=2)
            await self.db.commit()
            return {
                "response": str(exc),
                "error": True,
                "intent": intent.intent,
                "agent": agent_name,
            }

        # 5. Persist assistant message
        assistant_msg = ConversationMessage(
            session_id=session_id,
            role="assistant",
            content=result.response_text or "",
            agent=result.agent_name,
            intent=result.intent,
            entities={"source": intent.source},
            tool_calls=[tc.to_dict() for tc in result.tool_calls],
            tool_results=[tr.to_dict() for tr in result.tool_results],
            structured_output=result.structured_output,
            approval_request_id=(
                result.approval_request_ids[0] if result.approval_request_ids else None
            ),
            token_count=result.tokens_used,
            latency_ms=result.latency_ms,
            model_used=result.model_used,
            error=result.error,
        )
        self.db.add(assistant_msg)

        await self._bump_session(sess, count=2)
        await self.db.commit()

        # 6. Publish domain event (best-effort)
        try:
            await EventBus.publish_domain_event(
                domain="conversation",
                event_type="turn_completed",
                entity_id=str(session_id),
                entity_type="conversation_session",
                data={
                    "agent": result.agent_name,
                    "intent": result.intent,
                    "requires_human": result.requires_human,
                    "approvals": [str(a) for a in result.approval_request_ids],
                    "latency_ms": result.latency_ms,
                },
                actor_id=str(user_id),
                org_id=str(org_id),
            )
        except Exception:
            pass

        return {
            "response": result.response_text,
            "agent": result.agent_name,
            "intent": result.intent,
            "confidence": float(result.confidence) if result.confidence else None,
            "requires_human": result.requires_human,
            "approval_request_ids": [str(a) for a in result.approval_request_ids],
            "tool_calls": [tc.to_dict() for tc in result.tool_calls],
            "tool_results": [tr.to_dict() for tr in result.tool_results],
            "latency_ms": result.latency_ms,
        }

    @staticmethod
    async def _bump_session(sess: ConversationSession, count: int = 1) -> None:
        sess.last_message_at = datetime.now(timezone.utc)
        sess.message_count = (sess.message_count or 0) + count
