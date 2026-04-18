"""
Audit Service — writes to the append-only `audit_logs` table, chains
each row's `hash_signature` to the previous row's hash for tamper detection.

Hash chain: h_n = sha256(h_{n-1} || canonical_json(payload_n)).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, desc, select

from app.models.audit import AuditLog
from app.services._base import DomainService


@dataclass
class AuditEventInput:
    event_type: str                 # e.g. "finance.invoice.posted"
    event_category: str             # "finance" / "procurement" / ...
    severity: str = "info"          # info / warning / critical
    actor_type: str = "human"       # human / agent / system
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    entity_display: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    ai_confidence: Optional[Decimal] = None
    original_prompt: Optional[str] = None
    interpreted_intent: Optional[str] = None
    policy_checks: list[dict[str, Any]] = field(default_factory=list)
    approval_chain: list[dict[str, Any]] = field(default_factory=list)
    before_state: Optional[dict[str, Any]] = None
    after_state: Optional[dict[str, Any]] = None
    outcome: str = "success"
    error_message: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _json_default(o: Any) -> Any:
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, uuid.UUID):
        return str(o)
    raise TypeError(f"unserializable: {type(o).__name__}")


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_json_default)


def compute_hash(previous_hash: Optional[str], payload: dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update((previous_hash or "").encode("utf-8"))
    h.update(_canonical(payload).encode("utf-8"))
    return h.hexdigest()


class AuditService(DomainService):
    domain = "audit"

    async def record_event(self, evt: AuditEventInput) -> AuditLog:
        """Append an immutable audit row with hash-chained integrity."""
        prev = await self._latest_hash()
        event_id = f"EVT-{uuid.uuid4().hex[:24].upper()}"
        timestamp = datetime.now(timezone.utc)

        payload = {
            "event_id": event_id,
            "timestamp": timestamp.isoformat(),
            "org_id": str(self.org_id),
            "event_type": evt.event_type,
            "event_category": evt.event_category,
            "severity": evt.severity,
            "actor": {
                "type": evt.actor_type,
                "id": evt.actor_id,
                "name": evt.actor_name,
                "role": evt.actor_role,
            },
            "entity": {
                "type": evt.entity_type,
                "id": str(evt.entity_id) if evt.entity_id else None,
                "display": evt.entity_display,
            },
            "amount": str(evt.amount) if evt.amount is not None else None,
            "currency": evt.currency,
            "agent": {
                "id": evt.agent_id,
                "version": evt.agent_version,
                "confidence": str(evt.ai_confidence) if evt.ai_confidence is not None else None,
            },
            "policy_checks": evt.policy_checks,
            "approval_chain": evt.approval_chain,
            "before_state": evt.before_state,
            "after_state": evt.after_state,
            "outcome": evt.outcome,
            "metadata": evt.metadata,
        }
        hash_sig = compute_hash(prev, payload)

        row = AuditLog(
            org_id=self.org_id,
            event_id=event_id,
            timestamp=timestamp,
            event_type=evt.event_type,
            event_category=evt.event_category,
            severity=evt.severity,
            actor_type=evt.actor_type,
            actor_id=evt.actor_id,
            actor_name=evt.actor_name,
            actor_role=evt.actor_role,
            session_id=evt.session_id,
            ip_address=evt.ip_address,
            entity_type=evt.entity_type,
            entity_id=evt.entity_id,
            entity_display=evt.entity_display,
            amount=evt.amount,
            currency=evt.currency,
            agent_id=evt.agent_id,
            agent_version=evt.agent_version,
            ai_confidence=evt.ai_confidence,
            original_prompt=evt.original_prompt,
            interpreted_intent=evt.interpreted_intent,
            policy_checks=evt.policy_checks,
            approval_chain=evt.approval_chain,
            before_state=evt.before_state,
            after_state=evt.after_state,
            outcome=evt.outcome,
            error_message=evt.error_message,
            hash_signature=hash_sig,
            previous_hash=prev,
            metadata_json=evt.metadata,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def _latest_hash(self) -> Optional[str]:
        result = await self.db.execute(
            select(AuditLog.hash_signature)
            .where(AuditLog.org_id == self.org_id)
            .order_by(desc(AuditLog.timestamp))
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None

    # ---- Queries -----------------------------------------------------------

    async def list_events(
        self,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        actor_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        conds = [AuditLog.org_id == self.org_id]
        if event_type:
            conds.append(AuditLog.event_type == event_type)
        if event_category:
            conds.append(AuditLog.event_category == event_category)
        if actor_id:
            conds.append(AuditLog.actor_id == actor_id)
        if entity_type:
            conds.append(AuditLog.entity_type == entity_type)
        if entity_id:
            conds.append(AuditLog.entity_id == entity_id)
        if since:
            conds.append(AuditLog.timestamp >= since)
        if until:
            conds.append(AuditLog.timestamp <= until)
        result = await self.db.execute(
            select(AuditLog)
            .where(and_(*conds))
            .order_by(desc(AuditLog.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def verify_chain(self, limit: int = 1000) -> dict[str, Any]:
        """Walk the hash chain forward, verifying each row's hash.

        Returns `{verified: bool, checked: int, broken_at: event_id|None}`.
        """
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.org_id == self.org_id)
            .order_by(AuditLog.timestamp.asc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        prev: Optional[str] = None
        for row in rows:
            payload = {
                "event_id": row.event_id,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "org_id": str(row.org_id),
                "event_type": row.event_type,
                "event_category": row.event_category,
                "severity": row.severity,
                "actor": {
                    "type": row.actor_type,
                    "id": row.actor_id,
                    "name": row.actor_name,
                    "role": row.actor_role,
                },
                "entity": {
                    "type": row.entity_type,
                    "id": str(row.entity_id) if row.entity_id else None,
                    "display": row.entity_display,
                },
                "amount": str(row.amount) if row.amount is not None else None,
                "currency": row.currency,
                "agent": {
                    "id": row.agent_id,
                    "version": row.agent_version,
                    "confidence": str(row.ai_confidence) if row.ai_confidence is not None else None,
                },
                "policy_checks": row.policy_checks or [],
                "approval_chain": row.approval_chain or [],
                "before_state": row.before_state,
                "after_state": row.after_state,
                "outcome": row.outcome,
                "metadata": row.metadata_json or {},
            }
            expected = compute_hash(prev, payload)
            if expected != row.hash_signature or (row.previous_hash or None) != prev:
                return {
                    "verified": False,
                    "checked": rows.index(row),
                    "broken_at": row.event_id,
                }
            prev = row.hash_signature
        return {"verified": True, "checked": len(rows), "broken_at": None}
