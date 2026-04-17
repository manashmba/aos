"""
AOS Agent Bootstrap — registers router, domain agents, and orchestrator.

Call `bootstrap_agents()` during FastAPI startup (lifespan). After this,
the orchestrator is available via `get_orchestrator()` and the agent
registry is populated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.agents.llm import LLMClient
from app.agents.orchestrator import Orchestrator
from app.agents.registry import agent_registry
from app.agents.router_agent import RouterAgent
from app.agents.domain import (
    FinanceAgent,
    HRAgent,
    InventoryAgent,
    ManufacturingAgent,
    ProcurementAgent,
    ReportsAgent,
    SalesAgent,
)
from app.engine.policy import PolicyEngine


_POLICY_DIR = Path(__file__).resolve().parents[1] / "engine" / "policies"
_orchestrator: Optional[Orchestrator] = None
_bootstrapped: bool = False


def bootstrap_agents(force: bool = False) -> Orchestrator:
    """Idempotently register agents and build the orchestrator."""
    global _orchestrator, _bootstrapped

    if _bootstrapped and not force:
        assert _orchestrator is not None
        return _orchestrator

    llm = LLMClient()

    # Clear previous registrations if re-bootstrapping
    if force:
        agent_registry._agents.clear()  # type: ignore[attr-defined]

    # Router first
    if "router" not in agent_registry:
        agent_registry.register(RouterAgent(llm=llm))

    # Domain agents
    for cls in (
        FinanceAgent,
        ProcurementAgent,
        InventoryAgent,
        SalesAgent,
        HRAgent,
        ManufacturingAgent,
        ReportsAgent,
    ):
        inst = cls(llm=llm)
        if inst.name not in agent_registry:
            agent_registry.register(inst)

    policy = PolicyEngine.load_from_dir(_POLICY_DIR)
    _orchestrator = Orchestrator(policy_engine=policy, agents=agent_registry)
    _bootstrapped = True
    return _orchestrator


def get_orchestrator() -> Orchestrator:
    if _orchestrator is None:
        return bootstrap_agents()
    return _orchestrator
