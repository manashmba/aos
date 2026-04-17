"""
Finance Service — business logic for accounts, journals, invoices, payments.

Operates against the DB but does not itself persist the commit; callers
are expected to wrap ops in their own session/transaction.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import (
    Account,
    AccountType,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    JournalEntry,
    JournalLine,
    Payment,
    PaymentStatus,
)
from app.services._base import DomainError, DomainService


class FinanceService(DomainService):
    domain = "finance"

    # ---- Accounts ----------------------------------------------------------

    async def create_account(
        self,
        code: str,
        name: str,
        account_type: AccountType,
        parent_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        currency: str = "INR",
    ) -> Account:
        acct = Account(
            org_id=self.org_id,
            code=code,
            name=name,
            account_type=account_type,
            parent_id=parent_id,
            description=description,
            currency=currency,
        )
        self.db.add(acct)
        await self.db.flush()
        return acct

    async def get_account_by_code(self, code: str) -> Optional[Account]:
        result = await self.db.execute(
            select(Account).where(
                and_(Account.org_id == self.org_id, Account.code == code)
            )
        )
        return result.scalars().first()

    # ---- Journal Entries ---------------------------------------------------

    async def post_journal_entry(
        self,
        description: str,
        lines: list[dict[str, Any]],
        posted_by: uuid.UUID,
        idempotency_key: str,
        entry_date: Optional[date] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        fiscal_year: Optional[str] = None,
        fiscal_period: Optional[str] = None,
        approved_by: Optional[uuid.UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> JournalEntry:
        """
        Post a balanced journal entry.

        `lines` = [{"account_id": UUID, "debit": Decimal, "credit": Decimal,
                    "description": str?, "cost_center": str?}]
        """
        if not lines:
            raise DomainError("Journal entry must have at least two lines", "invalid_entry")

        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        for l in lines:
            total_debit += self._dec(l.get("debit", 0))
            total_credit += self._dec(l.get("credit", 0))

        if total_debit != total_credit:
            raise DomainError(
                f"Entry unbalanced: debits={total_debit}, credits={total_credit}",
                "unbalanced",
            )
        if total_debit == 0:
            raise DomainError("Entry has zero value", "zero_value")

        # Idempotency check
        existing = await self.db.execute(
            select(JournalEntry).where(JournalEntry.idempotency_key == idempotency_key)
        )
        prior = existing.scalars().first()
        if prior is not None:
            return prior

        edate = entry_date or date.today()
        fy = fiscal_year or self._fiscal_year_for(edate)
        fp = fiscal_period or f"{edate.month:02d}"

        entry_number = await self._next_entry_number()

        je = JournalEntry(
            org_id=self.org_id,
            entry_number=entry_number,
            entry_date=edate,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            posted_by=posted_by,
            approved_by=approved_by,
            idempotency_key=idempotency_key,
            fiscal_year=fy,
            fiscal_period=fp,
            metadata_json=metadata or {},
        )
        self.db.add(je)
        await self.db.flush()

        for l in lines:
            jl = JournalLine(
                journal_entry_id=je.id,
                account_id=l["account_id"],
                debit=self._dec(l.get("debit", 0)),
                credit=self._dec(l.get("credit", 0)),
                description=l.get("description"),
                cost_center=l.get("cost_center"),
                entity_type=l.get("entity_type"),
                entity_id=l.get("entity_id"),
            )
            self.db.add(jl)

        await self.db.flush()
        return je

    async def _next_entry_number(self) -> str:
        """Simple monotonic entry number per org per year."""
        year = datetime.now(timezone.utc).year
        prefix = f"JE-{year}-"
        result = await self.db.execute(
            select(func.count(JournalEntry.id)).where(
                and_(
                    JournalEntry.org_id == self.org_id,
                    JournalEntry.entry_number.like(f"{prefix}%"),
                )
            )
        )
        count = int(result.scalar() or 0) + 1
        return f"{prefix}{count:06d}"

    @staticmethod
    def _fiscal_year_for(d: date) -> str:
        """Indian FY: Apr–Mar."""
        if d.month >= 4:
            return f"FY{d.year}-{(d.year + 1) % 100:02d}"
        return f"FY{d.year - 1}-{d.year % 100:02d}"

    # ---- Trial balance -----------------------------------------------------

    async def trial_balance(
        self,
        as_of: Optional[date] = None,
    ) -> list[dict[str, Any]]:
        """Simple trial balance grouped by account."""
        cutoff = as_of or date.today()
        stmt = (
            select(
                Account.id,
                Account.code,
                Account.name,
                Account.account_type,
                func.coalesce(func.sum(JournalLine.debit), 0).label("debits"),
                func.coalesce(func.sum(JournalLine.credit), 0).label("credits"),
            )
            .join(JournalLine, JournalLine.account_id == Account.id, isouter=True)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id, isouter=True)
            .where(
                and_(
                    Account.org_id == self.org_id,
                    (JournalEntry.entry_date <= cutoff) | (JournalEntry.id.is_(None)),
                )
            )
            .group_by(Account.id, Account.code, Account.name, Account.account_type)
            .order_by(Account.code)
        )
        result = await self.db.execute(stmt)
        out = []
        for row in result.all():
            debits = self._dec(row.debits or 0)
            credits = self._dec(row.credits or 0)
            balance = debits - credits
            out.append({
                "account_id": str(row.id),
                "code": row.code,
                "name": row.name,
                "type": row.account_type.value if hasattr(row.account_type, "value") else str(row.account_type),
                "debits": str(debits),
                "credits": str(credits),
                "balance": str(balance),
            })
        return out

    # ---- Invoices ----------------------------------------------------------

    async def create_invoice(
        self,
        invoice_number: str,
        invoice_type: InvoiceType,
        invoice_date: date,
        due_date: date,
        total_amount: Decimal,
        subtotal: Decimal,
        tax_amount: Decimal = Decimal("0.00"),
        customer_id: Optional[uuid.UUID] = None,
        vendor_id: Optional[uuid.UUID] = None,
        gstin: Optional[str] = None,
        line_items: Optional[list[dict[str, Any]]] = None,
        po_reference: Optional[uuid.UUID] = None,
    ) -> Invoice:
        inv = Invoice(
            org_id=self.org_id,
            invoice_number=invoice_number,
            invoice_type=invoice_type,
            invoice_date=invoice_date,
            due_date=due_date,
            subtotal=self._dec(subtotal),
            tax_amount=self._dec(tax_amount),
            total_amount=self._dec(total_amount),
            customer_id=customer_id,
            vendor_id=vendor_id,
            gstin=gstin,
            line_items=line_items or [],
            po_reference=po_reference,
            status=InvoiceStatus.DRAFT,
        )
        self.db.add(inv)
        await self.db.flush()
        return inv

    async def ageing_buckets(
        self,
        as_of: Optional[date] = None,
        invoice_type: InvoiceType = InvoiceType.SALES,
    ) -> dict[str, Decimal]:
        """Classic 0-30 / 31-60 / 61-90 / 90+ ageing."""
        cutoff = as_of or date.today()
        result = await self.db.execute(
            select(Invoice).where(
                and_(
                    Invoice.org_id == self.org_id,
                    Invoice.invoice_type == invoice_type,
                    Invoice.status.in_([
                        InvoiceStatus.POSTED,
                        InvoiceStatus.APPROVED,
                        InvoiceStatus.PARTIALLY_PAID,
                    ]),
                )
            )
        )
        buckets = {
            "current": Decimal("0.00"),
            "1-30": Decimal("0.00"),
            "31-60": Decimal("0.00"),
            "61-90": Decimal("0.00"),
            "90+": Decimal("0.00"),
        }
        for inv in result.scalars():
            outstanding = (inv.total_amount or Decimal("0")) - (inv.paid_amount or Decimal("0"))
            if outstanding <= 0:
                continue
            days = (cutoff - inv.due_date).days
            if days <= 0:
                buckets["current"] += outstanding
            elif days <= 30:
                buckets["1-30"] += outstanding
            elif days <= 60:
                buckets["31-60"] += outstanding
            elif days <= 90:
                buckets["61-90"] += outstanding
            else:
                buckets["90+"] += outstanding
        return buckets

    # ---- Payments ----------------------------------------------------------

    async def create_payment(
        self,
        payment_type: str,   # inbound / outbound
        payment_mode: str,   # neft / rtgs / upi / cheque / cash
        amount: Decimal,
        payment_date: date,
        idempotency_key: str,
        vendor_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        invoice_id: Optional[uuid.UUID] = None,
        tds_amount: Decimal = Decimal("0.00"),
        tds_section: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Payment:
        if amount <= 0:
            raise DomainError("Payment amount must be positive", "invalid_amount")

        existing = await self.db.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        prior = existing.scalars().first()
        if prior is not None:
            return prior

        payment_number = await self._next_payment_number()
        pay = Payment(
            org_id=self.org_id,
            payment_number=payment_number,
            payment_type=payment_type,
            payment_mode=payment_mode,
            amount=self._dec(amount),
            payment_date=payment_date,
            vendor_id=vendor_id,
            customer_id=customer_id,
            invoice_id=invoice_id,
            idempotency_key=idempotency_key,
            tds_amount=self._dec(tds_amount),
            tds_section=tds_section,
            notes=notes,
            status=PaymentStatus.DRAFT,
        )
        self.db.add(pay)
        await self.db.flush()
        return pay

    async def _next_payment_number(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"PAY-{year}-"
        result = await self.db.execute(
            select(func.count(Payment.id)).where(
                and_(
                    Payment.org_id == self.org_id,
                    Payment.payment_number.like(f"{prefix}%"),
                )
            )
        )
        count = int(result.scalar() or 0) + 1
        return f"{prefix}{count:06d}"
