"""
AOS Approval Matrix — resolves who must approve a given action.

Backed by the `ApprovalRule` table so business users can edit the matrix
through the admin UI at runtime. Supports amount bands, role-based
routing, and multi-level chains (via `sequence`).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import ApprovalRule


@dataclass
class ResolvedApprover:
    """A single step in an approval chain."""

    sequence: int
    role: str
    is_parallel: bool = False
    escalation_after_hours: Optional[int] = None
    rule_id: Optional[uuid.UUID] = None
    approver_user_id: Optional[uuid.UUID] = None


@dataclass
class ApprovalChain:
    """A resolved approval chain for an action."""

    required: bool
    steps: list[ResolvedApprover] = field(default_factory=list)

    def to_dict(self) -> list[dict]:
        return [
            {
                "sequence": s.sequence,
                "role": s.role,
                "is_parallel": s.is_parallel,
                "escalation_after_hours": s.escalation_after_hours,
                "rule_id": str(s.rule_id) if s.rule_id else None,
                "approver_user_id": str(s.approver_user_id) if s.approver_user_id else None,
            }
            for s in self.steps
        ]


class ApprovalMatrix:
    """DB-backed approval matrix resolver."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def resolve(
        self,
        org_id: uuid.UUID,
        entity_type: str,
        amount: Optional[Decimal] = None,
    ) -> ApprovalChain:
        """Resolve the full approval chain for (org, entity_type, amount)."""
        now = datetime.now(timezone.utc)

        stmt = select(ApprovalRule).where(
            and_(
                ApprovalRule.org_id == org_id,
                ApprovalRule.entity_type == entity_type,
                ApprovalRule.is_active.is_(True),
                ApprovalRule.effective_from <= now,
                or_(
                    ApprovalRule.effective_until.is_(None),
                    ApprovalRule.effective_until >= now,
                ),
            )
        )

        result = await self.session.execute(stmt)
        rules = result.scalars().all()

        matched: list[ApprovalRule] = []
        for rule in rules:
            if self._matches_amount(rule, amount):
                matched.append(rule)

        matched.sort(key=lambda r: r.sequence or 1)

        steps = [
            ResolvedApprover(
                sequence=r.sequence or 1,
                role=r.approver_role,
                is_parallel=bool(r.is_parallel),
                escalation_after_hours=r.escalation_after_hours,
                rule_id=r.id,
                approver_user_id=r.approver_user_id,
            )
            for r in matched
        ]

        return ApprovalChain(required=bool(steps), steps=steps)

    @staticmethod
    def _matches_amount(rule: ApprovalRule, amount: Optional[Decimal]) -> bool:
        """Amount band check. Rules with no bounds always apply."""
        min_amt = rule.min_amount
        max_amt = rule.max_amount

        if amount is None:
            return (min_amt is None or min_amt == Decimal("0.00")) and max_amt is None

        if min_amt is not None and amount < min_amt:
            return False
        if max_amt is not None and amount > max_amt:
            return False
        return True
