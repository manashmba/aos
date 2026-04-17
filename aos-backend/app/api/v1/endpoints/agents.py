"""
AOS Agents API — list agents, route intent, run a single agent turn.

These endpoints are primarily for debugging and admin; the main
conversation flow goes through /conversation (Module 5).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.agents.base import AgentContext
from app.agents.bootstrap import get_orchestrator
from app.agents.registry import agent_registry
from app.agents.router_agent import RouterAgent
from app.core.dependencies import AuthUser, get_current_user

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentSummary(BaseModel):
    name: str
    description: str
    domain: str
    version: str
    intents: list[str]


class RouteRequest(BaseModel):
    message: str


class RouteResponse(BaseModel):
    intent: str
    domain: Optional[str]
    agent_name: Optional[str]
    confidence: float
    clarifying_question: Optional[str] = None


class RunAgentRequest(BaseModel):
    agent: str
    message: str


@router.get("", response_model=list[AgentSummary])
async def list_agents(_user: AuthUser = Depends(get_current_user)) -> list[AgentSummary]:
    return [
        AgentSummary(
            name=a.name,
            description=a.description,
            domain=a.domain,
            version=a.version,
            intents=a.supported_intents,
        )
        for a in agent_registry.all()
    ]


@router.post("/route", response_model=RouteResponse)
async def route(
    req: RouteRequest,
    user: AuthUser = Depends(get_current_user),
) -> RouteResponse:
    """Classify a user message — does not execute anything."""
    _ = get_orchestrator()  # ensure bootstrapped
    router_agent = agent_registry.get("router")
    if not isinstance(router_agent, RouterAgent):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Router agent unavailable")

    ctx = AgentContext(
        org_id=uuid.UUID(str(user.org_id)) if user.org_id else uuid.uuid4(),
        user_id=uuid.UUID(str(user.user_id)) if user.user_id else uuid.uuid4(),
        user_role=user.role,
    )
    decision = await router_agent.classify(req.message, ctx)
    return RouteResponse(
        intent=decision.intent,
        domain=decision.domain,
        agent_name=decision.agent_name,
        confidence=decision.confidence,
        clarifying_question=decision.clarifying_question,
    )


@router.post("/run")
async def run_agent(
    req: RunAgentRequest,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Run a named agent for one turn. Returns the full AgentResult."""
    orch = get_orchestrator()
    ctx = AgentContext(
        org_id=uuid.UUID(str(user.org_id)) if user.org_id else uuid.uuid4(),
        user_id=uuid.UUID(str(user.user_id)) if user.user_id else uuid.uuid4(),
        user_role=user.role,
    )
    result = await orch.run(req.agent, req.message, ctx)
    return result.to_dict()
