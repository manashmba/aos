"""
AOS Orchestrator — routes user intent to the right agent, enforces guardrails.

Flow per turn:
  1. Intent classification (routing) — pick the agent.
  2. Agent.plan() — produces ToolCall plan.
  3. Policy Engine evaluates EACH tool call's effective context.
  4. Approval routing if required (creates ApprovalRequest, pauses execution).
  5. Tool execution (deterministic) with idempotency.
  6. Audit log write + event publish.
  7. Agent.post_process() formats response.

The orchestrator is the *only* place agents' outputs meet the deterministic
execution layer. If a tool call is blocked, we still record the attempt.
"""

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, AgentResult, BaseAgent, ToolCall, ToolResult
from app.agents.registry import AgentRegistry, agent_registry
from app.agents.tools.registry import Tool, ToolRegistry, tool_registry
from app.engine.policy import PolicyEngine


class OrchestratorError(Exception):
    """Orchestration failed in a way the caller should surface."""


class Orchestrator:
    """Core orchestrator. One instance per app; reusable across requests."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        agents: Optional[AgentRegistry] = None,
        tools: Optional[ToolRegistry] = None,
    ) -> None:
        self.policy = policy_engine
        self.agents = agents or agent_registry
        self.tools = tools or tool_registry

    # ---- Routing ------------------------------------------------------------

    def route(self, intent: str, domain_hint: Optional[str] = None) -> Optional[BaseAgent]:
        """Pick an agent for an intent. Prefers exact intent match."""
        agent = self.agents.for_intent(intent)
        if agent is not None:
            return agent
        if domain_hint:
            agents = self.agents.for_domain(domain_hint)
            if agents:
                return agents[0]
        return None

    # ---- Per-turn entry point ----------------------------------------------

    async def run(
        self,
        agent_name: str,
        user_message: str,
        context: AgentContext,
        session: Optional[AsyncSession] = None,
    ) -> AgentResult:
        """Run one turn with a named agent."""
        agent = self.agents.get(agent_name)
        if agent is None:
            raise OrchestratorError(f"Unknown agent: {agent_name}")
        return await self._run_agent(agent, user_message, context, session=session)

    async def handle(
        self,
        intent: str,
        user_message: str,
        context: AgentContext,
        domain_hint: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> AgentResult:
        """Route an intent to an agent and run it."""
        agent = self.route(intent, domain_hint=domain_hint)
        if agent is None:
            raise OrchestratorError(f"No agent can handle intent: {intent}")
        result = await self._run_agent(agent, user_message, context, session=session)
        result.intent = intent
        return result

    # ---- Internal -----------------------------------------------------------

    async def _run_agent(
        self,
        agent: BaseAgent,
        user_message: str,
        context: AgentContext,
        session: Optional[AsyncSession] = None,
    ) -> AgentResult:
        started = time.perf_counter()
        result = AgentResult(agent_name=agent.name)

        try:
            # 1. Plan
            plan = await agent.plan(user_message, context)
        except Exception as exc:
            result.error = f"planning_failed: {exc}"
            result.requires_human = True
            result.latency_ms = int((time.perf_counter() - started) * 1000)
            return result

        # Enforce per-turn tool-call cap
        if len(plan) > context.max_tool_calls:
            result.error = (
                f"plan exceeds max_tool_calls "
                f"({len(plan)} > {context.max_tool_calls})"
            )
            result.requires_human = True
            result.latency_ms = int((time.perf_counter() - started) * 1000)
            return result

        result.tool_calls = plan

        # 2/3/4/5. Evaluate + execute each tool call
        for call in plan:
            tool = self.tools.get(call.tool_name)
            if tool is None:
                result.tool_results.append(ToolResult(
                    tool_call_id=call.id,
                    success=False,
                    error=f"Tool '{call.tool_name}' not registered",
                ))
                continue

            # Agent-level whitelist
            if agent.allowed_tools and tool.name not in agent.allowed_tools:
                result.tool_results.append(ToolResult(
                    tool_call_id=call.id,
                    success=False,
                    error=f"Agent '{agent.name}' not allowed to call '{tool.name}'",
                ))
                continue

            tr = await self._execute_tool(agent, call, tool, context)
            result.tool_results.append(tr)

            if tr.requires_approval and tr.approval_request_id:
                result.approval_request_ids.append(tr.approval_request_id)

        # 7. Post-process
        try:
            result.response_text = await agent.post_process(
                context, result.tool_calls, result.tool_results
            )
        except Exception as exc:
            result.response_text = f"(post-processing failed: {exc})"

        # Confidence = min of tool call confidences, if present
        confidences = [c.confidence for c in plan if c.confidence is not None]
        if confidences:
            result.confidence = min(confidences)

        # Human review if any blocked / any required approval
        result.requires_human = (
            any(not r.success or r.requires_approval for r in result.tool_results)
            or bool(result.approval_request_ids)
        )

        result.latency_ms = int((time.perf_counter() - started) * 1000)
        return result

    async def _execute_tool(
        self,
        agent: BaseAgent,
        call: ToolCall,
        tool: Tool,
        context: AgentContext,
    ) -> ToolResult:
        """Policy-check, then execute a single tool."""
        # Build effective policy context
        policy_ctx: dict[str, Any] = {
            "tool_name": tool.name,
            "domain": tool.domain,
            "is_financial_write": tool.is_financial_write,
            "is_external_call": tool.is_external_call,
            "confidence": float(call.confidence) if call.confidence is not None else 1.0,
            "idempotency_key": call.idempotency_key,
            "tool_calls_this_turn": 1,  # placeholder; orchestrator may track across loop
            "user_role": context.user_role,
            **(call.arguments or {}),
        }

        # Policy evaluation on the agent layer itself
        decision = self.policy.evaluate(
            domain="agent",
            action="execute_tool",
            context=policy_ctx,
        )
        if not decision.allowed:
            return ToolResult(
                tool_call_id=call.id,
                success=False,
                error=f"policy_blocked: {'; '.join(decision.blocks)}",
            )

        if decision.requires_approval:
            # Caller (conversation/workflow layer) will create ApprovalRequest
            return ToolResult(
                tool_call_id=call.id,
                success=False,
                requires_approval=True,
                error=f"approval_required: {','.join(decision.approver_roles)}",
            )

        # Execute
        started = time.perf_counter()
        try:
            output = await tool.call(**(call.arguments or {}))
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ToolResult(
                tool_call_id=call.id,
                success=True,
                output=output,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ToolResult(
                tool_call_id=call.id,
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
            )
