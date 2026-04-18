"""Audit API — list events, verify hash-chain integrity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import PlainTextResponse

from app.core.dependencies import AuthUser, DbSession, get_current_user
from app.core.metrics import metrics_response
from app.services.audit import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


def _svc(db, user: AuthUser) -> AuditService:
    return AuditService(db=db, org_id=uuid.UUID(str(user.org_id)))


def _serialize(row) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "event_id": row.event_id,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
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
        "agent_id": row.agent_id,
        "ai_confidence": str(row.ai_confidence) if row.ai_confidence is not None else None,
        "outcome": row.outcome,
        "hash_signature": row.hash_signature,
        "previous_hash": row.previous_hash,
    }


@router.get("/events")
async def list_events(
    db: DbSession,
    event_type: Optional[str] = None,
    event_category: Optional[str] = None,
    actor_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 100,
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    rows = await _svc(db, user).list_events(
        event_type=event_type,
        event_category=event_category,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        since=since,
        until=until,
        limit=min(limit, 1000),
    )
    return [_serialize(r) for r in rows]


@router.get("/verify")
async def verify_chain(
    db: DbSession,
    limit: int = 1000,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    return await _svc(db, user).verify_chain(limit=limit)


# ---- Metrics (unauthenticated — scrape endpoint) ---------------------------

metrics_router = APIRouter(tags=["observability"])


@metrics_router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> Response:
    body, ctype = metrics_response()
    return Response(content=body, media_type=ctype, status_code=status.HTTP_200_OK)
