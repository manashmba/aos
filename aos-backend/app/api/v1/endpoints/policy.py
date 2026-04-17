"""
AOS Policy API — inspect, evaluate, and reload business rules.

These endpoints let admins (CFOs, compliance officers) see every policy
that will affect an action, test hypothetical scenarios, and hot-reload
the ruleset after editing YAML.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import AuthUser, get_current_user
from app.engine.policy import PolicyEngine

router = APIRouter(prefix="/policy", tags=["policy"])


# ---- In-process singleton ----------------------------------------------------

_POLICY_DIR = Path(__file__).resolve().parents[4] / "engine" / "policies"
_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Lazily load the policy engine from the default policy directory."""
    global _engine
    if _engine is None:
        _engine = PolicyEngine.load_from_dir(_POLICY_DIR)
    return _engine


# ---- Schemas -----------------------------------------------------------------

class EvaluateRequest(BaseModel):
    domain: str = Field(..., examples=["procurement"])
    action: str = Field(..., examples=["create_purchase_order"])
    context: dict[str, Any] = Field(default_factory=dict)


class EvaluateResponse(BaseModel):
    allowed: bool
    requires_approval: bool
    approver_roles: list[str]
    blocks: list[str]
    warnings: list[str]
    effects: dict[str, Any]
    matched_rules: list[str]
    ruleset_version: str


class RuleSummary(BaseModel):
    id: str
    name: str
    domain: str
    action: str
    severity: str
    active: bool
    version: int


# ---- Endpoints ---------------------------------------------------------------

@router.get("/rules", response_model=list[RuleSummary])
async def list_rules(
    domain: Optional[str] = None,
    action: Optional[str] = None,
    _user: AuthUser = Depends(get_current_user),
) -> list[RuleSummary]:
    """List all policy rules, optionally filtered by domain and/or action."""
    engine = get_policy_engine()
    rules = [
        RuleSummary(
            id=r.id,
            name=r.name,
            domain=r.domain,
            action=r.action,
            severity=r.severity,
            active=r.active,
            version=r.version,
        )
        for r in engine.ruleset
        if (domain is None or r.domain == domain)
        and (action is None or r.action == action)
    ]
    return rules


@router.get("/rules/{rule_id}")
async def get_rule(
    rule_id: str,
    _user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the full body of a single rule."""
    engine = get_policy_engine()
    rule = engine.ruleset.get(rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Rule {rule_id} not found")
    return rule.to_dict()


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    req: EvaluateRequest,
    _user: AuthUser = Depends(get_current_user),
) -> EvaluateResponse:
    """Evaluate an action against the current ruleset. Does NOT execute anything."""
    engine = get_policy_engine()
    decision = engine.evaluate(req.domain, req.action, req.context)
    return EvaluateResponse(**decision.to_dict())


@router.post("/reload")
async def reload_rules(
    _user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Hot-reload the ruleset from disk. Requires admin role in production."""
    engine = get_policy_engine()
    engine.reload(_POLICY_DIR)
    return {
        "status": "ok",
        "rule_count": len(engine.ruleset),
        "version": engine.ruleset.version,
    }
