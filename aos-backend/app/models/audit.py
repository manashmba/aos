"""
AOS Audit Log Model
Immutable audit trail for every system action.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OrgScopedMixin, generate_uuid


class AuditLog(Base, OrgScopedMixin):
    """Immutable audit log — one row per business event.

    This table is APPEND-ONLY. No updates or deletes are permitted,
    enforced by DB trigger and application logic.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    event_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False)  # auth / finance / procurement etc.
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info / warning / critical

    # Actor
    actor_type: Mapped[str] = mapped_column(String(20), default="human")  # human / agent / system
    actor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    actor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Target entity
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    entity_display: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Financial context
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)

    # AI involvement
    agent_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agent_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ai_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    original_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interpreted_intent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Policy and approval
    policy_checks: Mapped[dict] = mapped_column(JSON, default=list)
    approval_chain: Mapped[dict] = mapped_column(JSON, default=list)

    # Before / after state
    before_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Outcome
    outcome: Mapped[str] = mapped_column(String(30), default="success")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Integrity
    hash_signature: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Full payload
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (
        Index("ix_audit_org_timestamp", "org_id", "timestamp"),
        Index("ix_audit_event_type", "event_type", "timestamp"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_actor", "actor_id", "timestamp"),
    )
