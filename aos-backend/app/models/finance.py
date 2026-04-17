"""
AOS Finance Models
General Ledger, Accounts Payable/Receivable, Tax, Bank Reconciliation.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Index,
    Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import OrgScopedMixin, TimestampMixin, generate_uuid

import enum


class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class InvoiceType(str, enum.Enum):
    SALES = "sales"
    PURCHASE = "purchase"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    POSTED = "posted"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    INITIATED = "initiated"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class Account(Base, TimestampMixin, OrgScopedMixin):
    """Chart of Accounts — GL account master."""
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    __table_args__ = (
        Index("ix_accounts_org_code", "org_id", "code", unique=True),
    )


class JournalEntry(Base, TimestampMixin, OrgScopedMixin):
    """Immutable journal entry header — the core of the ledger."""
    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    entry_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    posted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    fiscal_year: Mapped[str] = mapped_column(String(10), nullable=False)
    fiscal_period: Mapped[str] = mapped_column(String(10), nullable=False)
    is_reversal: Mapped[bool] = mapped_column(Boolean, default=False)
    reversal_of: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    lines = relationship("JournalLine", back_populates="journal_entry", lazy="selectin")

    __table_args__ = (
        Index("ix_je_org_date", "org_id", "entry_date"),
    )


class JournalLine(Base):
    """Individual debit/credit line in a journal entry."""
    __tablename__ = "journal_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cost_center: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Relationships
    journal_entry = relationship("JournalEntry", back_populates="lines")

    __table_args__ = (
        Index("ix_jl_account", "account_id", "journal_entry_id"),
    )


class Invoice(Base, TimestampMixin, OrgScopedMixin):
    """Sales and purchase invoices."""
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    invoice_type: Mapped[InvoiceType] = mapped_column(Enum(InvoiceType), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    irn: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    e_invoice_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    po_reference: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    grn_reference: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True)
    document_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    line_items: Mapped[dict] = mapped_column(JSON, default=list)

    __table_args__ = (
        Index("ix_invoices_org_number", "org_id", "invoice_number", unique=True),
        Index("ix_invoices_status", "org_id", "status"),
        Index("ix_invoices_due", "org_id", "due_date"),
    )


class Payment(Base, TimestampMixin, OrgScopedMixin):
    """Payment records — both inbound and outbound."""
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    payment_number: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # inbound / outbound
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # neft / rtgs / upi / cheque / cash
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    bank_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utr_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.DRAFT)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tds_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    tds_section: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_payments_org_number", "org_id", "payment_number", unique=True),
    )


class TaxRecord(Base, TimestampMixin, OrgScopedMixin):
    """GST, TDS, TCS tax computation records."""
    __tablename__ = "tax_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    tax_type: Mapped[str] = mapped_column(String(20), nullable=False)  # gst / tds / tcs
    tax_period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. 2024-10
    hsn_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cgst: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    sgst: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    igst: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    cess: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    vendor_gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    customer_gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    filing_status: Mapped[str] = mapped_column(String(20), default="pending")
    return_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # gstr1 / gstr3b / tds_26q


class BankTransaction(Base, TimestampMixin, OrgScopedMixin):
    """Bank statement entries for reconciliation."""
    __tablename__ = "bank_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    bank_account: Mapped[str] = mapped_column(String(50), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    matched_payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True)


class Reconciliation(Base, TimestampMixin, OrgScopedMixin):
    """Bank reconciliation sessions."""
    __tablename__ = "reconciliations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    bank_account: Mapped[str] = mapped_column(String(50), nullable=False)
    bank_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    book_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    difference: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    reconciled_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    unmatched_items: Mapped[dict] = mapped_column(JSON, default=list)
