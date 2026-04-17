"""
AOS Agent Registry — lookup of instantiated domain agents.

The orchestrator uses this registry to route intents to the correct agent.
"""

from __future__ import annotations

from typing import Optional

from app.agents.base import BaseAgent


class AgentRegistry:
    """Singleton-style registry of instantiated agents."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' already registered")
        self._agents[agent.name] = agent

    def get(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def all(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def for_intent(self, intent: str) -> Optional[BaseAgent]:
        for agent in self._agents.values():
            if agent.can_handle_intent(intent):
                return agent
        return None

    def for_domain(self, domain: str) -> list[BaseAgent]:
        return [a for a in self._agents.values() if a.domain == domain]

    def __contains__(self, name: str) -> bool:
        return name in self._agents


agent_registry = AgentRegistry()
