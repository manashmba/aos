"""
AOS Router Agent — classifies user intent and picks a domain agent.

This is the *entry* agent for every conversation turn. It doesn't execute
business tools directly; it returns a structured intent + chosen agent.
If intent is ambiguous, it asks a clarifying question.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from app.agents.base import AgentContext, BaseAgent, ToolCall
from app.agents.llm import LLMClient


@dataclass
class RouteDecision:
    intent: str
    agent_name: Optional[str]
    domain: Optional[str]
    confidence: float
    clarifying_question: Optional[str] = None


SYSTEM_PROMPT = """You are the AOS Router. You classify a user's message into an ERP intent.

Supported domains and example intents:
  - finance         (post_journal_entry, create_payment, run_payroll, file_gstr, reconcile_bank)
  - procurement    (create_purchase_order, approve_po, post_vendor_invoice, onboard_vendor)
  - inventory      (check_stock, stock_adjustment, reorder_check, dispatch_stock)
  - sales          (create_sales_order, create_quotation, apply_discount, check_credit)
  - manufacturing  (create_production_order, update_bom, release_workorder)
  - hr             (apply_leave, submit_reimbursement, revise_salary, onboard_employee)
  - reports        (generate_report, run_analytics, explain_variance)
  - general        (greeting, help, capability_query)

Return ONLY a JSON object:
  {"intent": "<snake_case_intent>",
   "domain": "<one_of_above>",
   "confidence": 0.0-1.0,
   "clarifying_question": "<only if confidence < 0.6, else null>"}
"""


class RouterAgent(BaseAgent):
    name = "router"
    description = "Classifies intent and picks a domain agent."
    domain = "general"
    supported_intents = ["*"]  # handles all
    system_prompt = SYSTEM_PROMPT

    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self.llm = llm or LLMClient()

    async def plan(self, user_message: str, context: AgentContext) -> list[ToolCall]:
        """The router doesn't plan tools; it returns an empty plan.
        Use `classify()` instead for the structured routing decision."""
        return []

    async def classify(self, user_message: str, context: AgentContext) -> RouteDecision:
        """Run the LLM to produce a routing decision."""
        try:
            resp = await self.llm.complete(
                system=self.system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=300,
                temperature=0.0,
            )
            data = self._extract_json(resp.text)
        except Exception:
            return RouteDecision(
                intent="unknown",
                agent_name=None,
                domain=None,
                confidence=0.0,
                clarifying_question="Could you please rephrase your request?",
            )

        intent = str(data.get("intent") or "unknown")
        domain = data.get("domain")
        confidence = float(data.get("confidence") or 0.0)
        clarify = data.get("clarifying_question")

        # Heuristic: map domain to canonical domain agent name
        agent_name = f"{domain}_agent" if domain else None

        return RouteDecision(
            intent=intent,
            agent_name=agent_name,
            domain=domain,
            confidence=confidence,
            clarifying_question=clarify,
        )

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract the first JSON object from a text response."""
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {}
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return {}
