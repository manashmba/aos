"""
AOS Intent Classifier — wraps RouterAgent with fast heuristics fallback.

Heuristic path runs first (cheap, zero-LLM). LLM routing engages only when
heuristics return low confidence. This matters for WhatsApp scale.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Optional

from app.agents.base import AgentContext
from app.agents.registry import agent_registry
from app.agents.router_agent import RouterAgent


@dataclass
class IntentResult:
    intent: str
    domain: Optional[str]
    agent_name: Optional[str]
    confidence: float
    clarifying_question: Optional[str] = None
    source: str = "llm"  # heuristic / llm / cached


# Very light keyword heuristics. Full intent tree lives in Router LLM.
_HEURISTICS: list[tuple[re.Pattern[str], str, str, str]] = [
    (re.compile(r"\b(create|raise|make)\s+(a\s+)?(po|purchase\s*order)\b", re.I),
     "create_purchase_order", "procurement", "procurement_agent"),
    (re.compile(r"\bapprove\s+(the\s+)?po\b", re.I),
     "approve_po", "procurement", "procurement_agent"),
    (re.compile(r"\b(pay|make\s+payment|schedule\s+payment)\b", re.I),
     "create_payment", "finance", "finance_agent"),
    (re.compile(r"\b(journal|voucher)\s+(entry|posting)\b", re.I),
     "post_journal_entry", "finance", "finance_agent"),
    (re.compile(r"\b(stock|inventory)\s+(level|available|check)\b", re.I),
     "check_stock", "inventory", "inventory_agent"),
    (re.compile(r"\b(apply|request)\s+leave\b", re.I),
     "apply_leave", "hr", "hr_agent"),
    (re.compile(r"\b(reimburs|expense)\b", re.I),
     "submit_reimbursement", "hr", "hr_agent"),
    (re.compile(r"\b(sales\s*order|new\s+order|create\s+so)\b", re.I),
     "create_sales_order", "sales", "sales_agent"),
    (re.compile(r"\b(report|analytics|variance|kpi)\b", re.I),
     "generate_report", "reports", "reports_agent"),
    (re.compile(r"\b(hello|hi|hey|help|what\s+can\s+you\s+do)\b", re.I),
     "greeting", "general", "router"),
]


class IntentClassifier:
    """Hybrid heuristic + LLM intent classifier."""

    def __init__(self, router_agent: Optional[RouterAgent] = None) -> None:
        self._router = router_agent

    def _get_router(self) -> Optional[RouterAgent]:
        if self._router is not None:
            return self._router
        r = agent_registry.get("router")
        return r if isinstance(r, RouterAgent) else None

    async def classify(
        self,
        message: str,
        context: AgentContext,
        min_heuristic_confidence: float = 0.85,
    ) -> IntentResult:
        # 1. Heuristic pass
        for pattern, intent, domain, agent_name in _HEURISTICS:
            if pattern.search(message):
                return IntentResult(
                    intent=intent,
                    domain=domain,
                    agent_name=agent_name,
                    confidence=min_heuristic_confidence,
                    source="heuristic",
                )

        # 2. LLM fallback
        router = self._get_router()
        if router is None:
            return IntentResult(
                intent="unknown",
                domain=None,
                agent_name=None,
                confidence=0.0,
                clarifying_question="Could you rephrase your request?",
                source="heuristic",
            )

        decision = await router.classify(message, context)
        return IntentResult(
            intent=decision.intent,
            domain=decision.domain,
            agent_name=decision.agent_name,
            confidence=decision.confidence,
            clarifying_question=decision.clarifying_question,
            source="llm",
        )
