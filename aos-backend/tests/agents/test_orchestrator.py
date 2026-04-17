"""Tests for agent orchestrator, tool registry, and policy guardrails."""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

import pytest

from app.agents.base import AgentContext, BaseAgent, ToolCall
from app.agents.orchestrator import Orchestrator
from app.agents.registry import AgentRegistry
from app.agents.tools.registry import ToolRegistry, register_tool, tool_registry
from app.engine.policy import PolicyEngine


POLICY_DIR = Path(__file__).resolve().parents[2] / "app" / "engine" / "policies"


class _EchoAgent(BaseAgent):
    name = "echo"
    description = "Test echo agent"
    domain = "test"
    supported_intents = ["echo"]
    system_prompt = "Echo."

    async def plan(self, user_message: str, context: AgentContext) -> list[ToolCall]:
        return [ToolCall(
            id="tc1",
            tool_name="test_echo",
            arguments={"msg": user_message},
            confidence=Decimal("0.95"),
        )]


def _make_ctx() -> AgentContext:
    return AgentContext(
        org_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        user_role="employee",
    )


@pytest.fixture
def registries():
    reg = AgentRegistry()
    reg.register(_EchoAgent())
    tools = ToolRegistry()

    async def echo(msg: str) -> dict:
        return {"echoed": msg}

    from app.agents.tools.registry import Tool
    tools.register(Tool(
        name="test_echo",
        description="test",
        domain="test",
        handler=echo,
    ))
    return reg, tools


@pytest.mark.asyncio
async def test_orchestrator_executes_plan(registries):
    agents, tools = registries
    policy = PolicyEngine.load_from_dir(POLICY_DIR)
    orch = Orchestrator(policy_engine=policy, agents=agents, tools=tools)

    result = await orch.run("echo", "hello", _make_ctx())
    assert not result.error
    assert len(result.tool_results) == 1
    assert result.tool_results[0].success is True
    assert result.tool_results[0].output == {"echoed": "hello"}


@pytest.mark.asyncio
async def test_orchestrator_enforces_tool_cap(registries):
    agents, tools = registries
    policy = PolicyEngine.load_from_dir(POLICY_DIR)
    orch = Orchestrator(policy_engine=policy, agents=agents, tools=tools)

    ctx = _make_ctx()
    ctx.max_tool_calls = 0
    result = await orch.run("echo", "hello", ctx)
    assert result.error is not None
    assert "max_tool_calls" in result.error


@pytest.mark.asyncio
async def test_unknown_tool_is_reported(registries):
    agents, tools = registries
    policy = PolicyEngine.load_from_dir(POLICY_DIR)

    class _BadPlanAgent(BaseAgent):
        name = "bad"
        description = "bad"
        domain = "test"
        supported_intents = ["bad"]
        system_prompt = "bad"
        async def plan(self, user_message, context):
            return [ToolCall(id="x", tool_name="missing_tool", arguments={})]

    agents.register(_BadPlanAgent())
    orch = Orchestrator(policy_engine=policy, agents=agents, tools=tools)
    result = await orch.run("bad", "hi", _make_ctx())
    assert result.tool_results[0].success is False
    assert "not registered" in (result.tool_results[0].error or "")


def test_tool_registry_schema_shape():
    from app.agents.tools.registry import Tool
    tools = ToolRegistry()

    async def h():
        return None

    tools.register(Tool(
        name="x",
        description="d",
        domain="test",
        handler=h,
        parameters_schema={
            "type": "object",
            "properties": {"a": {"type": "string"}},
            "required": ["a"],
        },
    ))
    schemas = tools.schemas(["x"])
    assert len(schemas) == 1
    assert schemas[0]["name"] == "x"
    assert schemas[0]["input_schema"]["properties"]["a"]["type"] == "string"


def test_agent_registry_routing():
    reg = AgentRegistry()
    reg.register(_EchoAgent())
    assert reg.get("echo") is not None
    assert reg.for_intent("echo") is not None
    assert reg.for_intent("nope") is None
