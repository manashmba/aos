"""
Ledger Engine — orchestrates deterministic posting.

Takes a business event (e.g. `sales.invoice_posted`) + context, resolves
the posting rule, looks up account ids by code, and delegates to
FinanceService.post_journal_entry to write a balanced, idempotent JE.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.ledger.fiscal import FiscalCalendar, fiscal_period_for, fiscal_year_for
from app.engine.ledger.posting_rules import POSTING_RULES
from app.models.finance import Account, JournalEntry
from app.services.finance import FinanceService


class PostingError(Exception):
    def __init__(self, message: str, code: str = "posting_error"):
        super().__init__(message)
        self.code = code


class LedgerEngine:
    def __init__(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        fiscal_calendar: Optional[FiscalCalendar] = None,
    ):
        self.db = db
        self.org_id = org_id
        self.fiscal = fiscal_calendar or FiscalCalendar()
        self.finance = FinanceService(db=db, org_id=org_id)
        self._account_cache: dict[str, uuid.UUID] = {}

    async def post_event(
        self,
        event: str,
        context: dict[str, Any],
        posted_by: uuid.UUID,
        idempotency_key: str,
        entry_date: Optional[date] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        approved_by: Optional[uuid.UUID] = None,
    ) -> JournalEntry:
        """Post a journal entry for the named business event.

        Idempotent — re-calling with the same `idempotency_key` returns the
        prior entry without creating a new one.
        """
        rule = POSTING_RULES.get(event)
        if rule is None:
            raise PostingError(f"No posting rule for event '{event}'", "unknown_event")

        edate = entry_date or date.today()
        if self.fiscal.is_locked(edate):
            raise PostingError(
                f"Fiscal period {fiscal_year_for(edate)}/{fiscal_period_for(edate)} is locked",
                "posting_period_locked",
            )

        try:
            raw_lines = rule.build_lines(context)
        except KeyError as e:
            raise PostingError(f"Missing field in context: {e}", "invalid_context") from e

        if not raw_lines:
            raise PostingError("Posting rule produced no lines", "empty_posting")

        # Resolve account codes to ids
        resolved: list[dict[str, Any]] = []
        total_d = Decimal("0")
        total_c = Decimal("0")
        for l in raw_lines:
            code = l["account_code"]
            acct_id = await self._account_id_for(code)
            if acct_id is None:
                raise PostingError(
                    f"Account with code '{code}' not found for org",
                    "account_not_found",
                )
            debit = Decimal(str(l.get("debit") or 0))
            credit = Decimal(str(l.get("credit") or 0))
            total_d += debit
            total_c += credit
            resolved.append({
                "account_id": acct_id,
                "debit": debit,
                "credit": credit,
                "description": l.get("description"),
                "cost_center": l.get("cost_center"),
                "entity_type": l.get("entity_type"),
                "entity_id": l.get("entity_id"),
            })

        if total_d != total_c:
            raise PostingError(
                f"Rule '{event}' produced unbalanced lines: debits={total_d} credits={total_c}",
                "unbalanced",
            )

        je = await self.finance.post_journal_entry(
            description=f"{rule.description} — {context.get('reference', event)}",
            lines=resolved,
            posted_by=posted_by,
            idempotency_key=idempotency_key,
            entry_date=edate,
            reference_type=reference_type or event.split(".")[0],
            reference_id=reference_id,
            approved_by=approved_by,
            metadata={"event": event, "context_ref": context.get("reference")},
        )
        return je

    async def _account_id_for(self, code: str) -> Optional[uuid.UUID]:
        if code in self._account_cache:
            return self._account_cache[code]
        result = await self.db.execute(
            select(Account.id).where(
                and_(Account.org_id == self.org_id, Account.code == code)
            )
        )
        row = result.first()
        if row is None:
            return None
        self._account_cache[code] = row[0]
        return row[0]

    async def preload_accounts(self, codes: list[str]) -> None:
        """Warm the account-id cache for known codes."""
        result = await self.db.execute(
            select(Account.code, Account.id).where(
                and_(Account.org_id == self.org_id, Account.code.in_(codes))
            )
        )
        for code, acct_id in result.all():
            self._account_cache[code] = acct_id
