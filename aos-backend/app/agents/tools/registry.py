"""
AOS Tool Registry — a global catalog of tools agents can invoke.

Tools are:
  - Named, versioned callables with a JSON schema for arguments.
  - Tagged with domain + required permission + whether they are financial writes.
  - Registered once at import time via @register_tool(...).
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


ToolHandler = Callable[..., Awaitable[Any]]


@dataclass
class Tool:
    """Metadata + handler for a single tool."""

    name: str
    description: str
    domain: str
    handler: ToolHandler
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    required_permission: Optional[str] = None
    is_financial_write: bool = False
    is_external_call: bool = False
    version: str = "1.0.0"

    def to_schema(self) -> dict[str, Any]:
        """LLM-friendly tool schema (Anthropic / OpenAI compatible shape)."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters_schema or {
                "type": "object",
                "properties": {},
                "additionalProperties": True,
            },
        }

    async def call(self, **kwargs: Any) -> Any:
        """Invoke the handler, awaiting if needed."""
        result = self.handler(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result


class ToolRegistry:
    """Singleton-style registry of tools available to agents."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def require(self, name: str) -> Tool:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' not found in registry")
        return tool

    def list(self, domain: Optional[str] = None) -> list[Tool]:
        if domain is None:
            return list(self._tools.values())
        return [t for t in self._tools.values() if t.domain == domain]

    def schemas(self, names: Optional[list[str]] = None) -> list[dict[str, Any]]:
        """Return LLM-ready schemas for the given tool names (or all)."""
        if names is None:
            return [t.to_schema() for t in self._tools.values()]
        out = []
        for n in names:
            t = self._tools.get(n)
            if t is not None:
                out.append(t.to_schema())
        return out

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


tool_registry = ToolRegistry()


def register_tool(
    name: str,
    description: str,
    domain: str,
    parameters_schema: Optional[dict[str, Any]] = None,
    required_permission: Optional[str] = None,
    is_financial_write: bool = False,
    is_external_call: bool = False,
    version: str = "1.0.0",
) -> Callable[[ToolHandler], ToolHandler]:
    """Decorator: register an async function as a tool."""

    def decorator(fn: ToolHandler) -> ToolHandler:
        tool_registry.register(Tool(
            name=name,
            description=description,
            domain=domain,
            handler=fn,
            parameters_schema=parameters_schema or {},
            required_permission=required_permission,
            is_financial_write=is_financial_write,
            is_external_call=is_external_call,
            version=version,
        ))
        return fn

    return decorator
