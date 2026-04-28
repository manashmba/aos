"""
AOS Conversation API — chat turns, session management, history.

This is the main entry point for the web/app UI and is also invoked
by the WhatsApp bot bridge (Module 11).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.agents.bootstrap import get_orchestrator
from app.core.dependencies import AuthUser, DbSession, get_current_user
from app.core.i18n import normalize as normalize_lang
from app.services.conversation import ConversationService

router = APIRouter(prefix="/conversation", tags=["conversation"])


# ---- Schemas ---------------------------------------------------------------

class StartSessionRequest(BaseModel):
    channel: str = Field("web", pattern="^(web|whatsapp|voice|email|api)$")
    language: str = Field("en", max_length=10)
    title: Optional[str] = Field(None, max_length=500)


class SessionResponse(BaseModel):
    id: uuid.UUID
    channel: str
    language: str
    title: Optional[str]
    status: str
    message_count: int


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    # Optional per-turn override. Falls back to session.language, then to the
    # value resolved by LanguageMiddleware. Lets a user temporarily switch
    # languages mid-session without resetting the session record.
    language: Optional[str] = Field(None, max_length=10)


class MessageResponse(BaseModel):
    response: Optional[str] = None
    agent: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    requires_human: bool = False
    requires_clarification: bool = False
    approval_request_ids: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: Optional[int] = None
    error: bool = False


# ---- Helpers ---------------------------------------------------------------

def _get_service(db) -> ConversationService:
    return ConversationService(db=db, orchestrator=get_orchestrator())


def _uuid(value: Any) -> uuid.UUID:
    return uuid.UUID(str(value))


# ---- Endpoints -------------------------------------------------------------

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    req: StartSessionRequest,
    db: DbSession,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> SessionResponse:
    svc = _get_service(db)
    # Body wins; otherwise inherit whatever LanguageMiddleware negotiated
    # from headers. Both are coerced through normalize() so an unsupported
    # code never makes it into the DB.
    chosen = normalize_lang(req.language or getattr(request.state, "language", None))
    sess = await svc.start_session(
        org_id=_uuid(user.org_id),
        user_id=_uuid(user.user_id),
        channel=req.channel,
        language=chosen,
        title=req.title,
    )
    return SessionResponse(
        id=sess.id,
        channel=sess.channel,
        language=sess.language,
        title=sess.title,
        status=sess.status,
        message_count=sess.message_count or 0,
    )


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: uuid.UUID,
    req: MessageRequest,
    db: DbSession,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> MessageResponse:
    svc = _get_service(db)
    sess = await svc.get_session(session_id)
    if sess is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    if str(sess.org_id) != str(user.org_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Session belongs to another org")

    # Per-turn precedence: explicit body > middleware-negotiated header > session default.
    turn_language = normalize_lang(
        req.language
        or getattr(request.state, "language", None)
        or sess.language
    )

    data = await svc.handle_turn(
        session_id=session_id,
        org_id=_uuid(user.org_id),
        user_id=_uuid(user.user_id),
        user_role=user.role,
        message=req.message,
        channel=sess.channel,
        language=turn_language,
    )
    return MessageResponse(
        response=data.get("response"),
        agent=data.get("agent"),
        intent=data.get("intent"),
        confidence=data.get("confidence"),
        requires_human=bool(data.get("requires_human")),
        requires_clarification=bool(data.get("requires_clarification")),
        approval_request_ids=data.get("approval_request_ids", []),
        tool_calls=data.get("tool_calls", []),
        tool_results=data.get("tool_results", []),
        latency_ms=data.get("latency_ms"),
        error=bool(data.get("error")),
    )


@router.get("/sessions/{session_id}/history")
async def get_history(
    session_id: uuid.UUID,
    db: DbSession,
    limit: int = 50,
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    svc = _get_service(db)
    sess = await svc.get_session(session_id)
    if sess is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    if str(sess.org_id) != str(user.org_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Session belongs to another org")
    return await svc.memory.get_history(session_id, limit=limit)


@router.post("/sessions/{session_id}/end", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(
    session_id: uuid.UUID,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> None:
    svc = _get_service(db)
    sess = await svc.get_session(session_id)
    if sess is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    if str(sess.org_id) != str(user.org_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Session belongs to another org")
    await svc.end_session(session_id)
