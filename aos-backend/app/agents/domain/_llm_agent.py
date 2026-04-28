"""
Shared base for LLM-driven domain agents.

An LLMDomainAgent:
  - Has a domain-specific system prompt describing its job + tools.
  - Loads tool schemas from the registry filtered by its `domain`.
  - Uses LLM tool-calling to produce a structured ToolCall plan.
  - Falls back to a safe "clarify" response if parsing fails.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from app.agents.base import AgentContext, BaseAgent, ToolCall
from app.agents.llm import LLMClient
from app.agents.tools.registry import ToolRegistry, tool_registry
from app.core.i18n import with_language_directive


class LLMDomainAgent(BaseAgent):
    """Base for domain agents that use LLM tool-calling to produce plans."""

    tool_domain: str = "general"  # filter tools by this domain

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        tools: Optional[ToolRegistry] = None,
    ) -> None:
        self.llm = llm or LLMClient()
        self.tools = tools or tool_registry

    def _available_tool_schemas(self) -> list[dict]:
        tools = self.tools.list(domain=self.tool_domain)
        if self.allowed_tools:
            tools = [t for t in tools if t.name in self.allowed_tools]
        return [t.to_schema() for t in tools]

    async def plan(self, user_message: str, context: AgentContext) -> list[ToolCall]:
        schemas = self._available_tool_schemas()
        if not schemas:
            return []

        messages = [{"role": "user", "content": user_message}]
        # Localize the system prompt so the LLM responds in the user's language.
        # The directive is appended (not prepended) so static prefix stays
        # cache-eligible across different locales.
        system = with_language_directive(self.system_prompt, context.language)
        try:
            resp = await self.llm.complete(
                system=system,
                messages=messages,
                tools=schemas,
                max_tokens=2048,
                temperature=0.1,
            )
        except Exception:
            return []

        plan: list[ToolCall] = []
        for tc in resp.tool_calls:
            plan.append(ToolCall(
                id=tc.get("id") or uuid.uuid4().hex,
                tool_name=tc.get("name", ""),
                arguments=tc.get("input") or {},
                confidence=Decimal("0.85"),  # default; refined later by self-reflect
            ))

        return plan
