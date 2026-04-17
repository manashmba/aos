"""
AOS Conversation Models
Session and message tracking for agent interactions.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import OrgScopedMixin, TimestampMixin, generate_uuid


class ConversationSession(Base, TimestampMixin, OrgScopedMixin):
    """A conversation session (thread) between a user and the AOS."""
    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    channel: Mapped[str] = mapped_column(String(20), default="web")  # web / whatsapp / voice / email / api
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active / ended
    language: Mapped[str] = mapped_column(String(10), default="en")
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    context: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    messages = relationship("ConversationMessage", back_populates="session", lazy="selectin")

    __table_args__ = (
        Index("ix_sess_user_active", "user_id", "status"),
    )


class ConversationMessage(Base, TimestampMixin):
    """Individual message within a conversation."""
    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversation_sessions.id"))
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant / system / tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entities: Mapped[dict] = mapped_column(JSON, default=dict)
    tool_calls: Mapped[dict] = mapped_column(JSON, default=list)
    tool_results: Mapped[dict] = mapped_column(JSON, default=list)
    structured_output: Mapped[dict] = mapped_column(JSON, default=dict)
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    approval_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session = relationship("ConversationSession", back_populates="messages")

    __table_args__ = (
        Index("ix_msg_session_created", "session_id", "created_at"),
    )
