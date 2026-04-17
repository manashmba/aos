"""Shared helpers for domain services."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class DomainError(Exception):
    """Raised for expected business-rule violations in domain services."""

    def __init__(self, message: str, code: str = "domain_error") -> None:
        super().__init__(message)
        self.code = code


class DomainService:
    """Base class for domain services. Holds a DB session and org scope."""

    domain: str = "general"

    def __init__(self, db: AsyncSession, org_id: uuid.UUID) -> None:
        self.db = db
        self.org_id = org_id

    def _dec(self, value: Any) -> Decimal:
        return value if isinstance(value, Decimal) else Decimal(str(value))
