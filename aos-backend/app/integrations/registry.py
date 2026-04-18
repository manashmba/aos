"""Integration registry — name → adapter instance lookup."""

from __future__ import annotations

from typing import Any, Optional


class IntegrationError(Exception):
    def __init__(self, message: str, code: str = "integration_error"):
        super().__init__(message)
        self.code = code


class IntegrationRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Any] = {}

    def register(self, name: str, provider: Any) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> Any:
        if name not in self._providers:
            raise IntegrationError(f"No integration registered: {name}", "not_registered")
        return self._providers[name]

    def has(self, name: str) -> bool:
        return name in self._providers

    def list(self) -> list[str]:
        return sorted(self._providers.keys())


_registry = IntegrationRegistry()


def register_integration(name: str, provider: Any) -> None:
    _registry.register(name, provider)


def get_integration(name: str) -> Any:
    return _registry.get(name)


def integration_registry() -> IntegrationRegistry:
    return _registry
