"""
External integration adapters.

Each sub-package provides a protocol + at least one implementation
(mock for local dev, real provider for prod). Adapters are injected
via `app.integrations.registry.get_integration(name)`.
"""
from app.integrations.registry import (
    IntegrationError,
    IntegrationRegistry,
    get_integration,
    register_integration,
)

__all__ = [
    "IntegrationError",
    "IntegrationRegistry",
    "get_integration",
    "register_integration",
]
