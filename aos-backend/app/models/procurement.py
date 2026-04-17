"""
AOS Procurement Models
Vendor management, Purchase Orders, GRN, Invoice Matching.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
import enum

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Index,
    Integer, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import OrgScopedMixin, TimestampMixin, generate_uuid


class VendorStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    BLACKLISTED = "blacklisted"
    INACTIVE = "inactive"


class POStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    PARTIALLY_RECEIVED = "partially_received"
    FULLY_RECEIVED = "fully_received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class Vendor(Base, TimestampMixin, OrgScopedMixin):
    """Vendor / supplier master."""
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pan: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bank_account: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[VendorStatus] = mapped_column(Enum(VendorStatus), default=VendorStatus.PENDING)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    tds_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    tds_section: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tds_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    categories: Mapped[dict] = mapped_column(JSON, default=list)
    rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 1), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (
        Index("ix_vendors_org_code", "org_id", "code", unique=True),
        Index("ix_vendors_org_name", "org_id", "name"),
    )


class PurchaseRequest(Base, TimestampMixin, OrgScopedMixin):
    """Purchase requisition — internal request for procurement."""
    __tablename__ = "purchase_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    pr_number: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), default="NOS")
    estimated_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    estimated_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    required_by: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    po_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual / auto_reorder / agent

    __table_args__ = (
        Index("ix_pr_org_number", "org_id", "pr_number", unique=True),
    )


class PurchaseOrder(Base, TimestampMixin, OrgScopedMixin):
    """Purchase order header."""
    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    po_number: Mapped[str] = mapped_column(String(50), nullable=False)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_delivery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    delivery_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[POStatus] = mapped_column(Enum(POStatus), default=POStatus.DRAFT)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sent_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sent_via: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # email / whatsapp / both
    special_terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    lines = relationship("PurchaseOrderLine", back_populates="purchase_order", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")

    __table_args__ = (
        Index("ix_po_org_number", "org_id", "po_number", unique=True),
        Index("ix_po_org_status", "org_id", "status"),
        Index("ix_po_org_vendor", "org_id", "vendor_id"),
    )


class PurchaseOrderLine(Base):
    """Purchase order line item."""
    __tablename__ = "purchase_order_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    po_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"))
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), default="NOS")
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    hsn_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="lines")


class GoodsReceipt(Base, TimestampMixin, OrgScopedMixin):
    """Goods Receipt Note (GRN) — receipt of goods against PO."""
    __tablename__ = "goods_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    grn_number: Mapped[str] = mapped_column(String(50), nullable=False)
    po_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"))
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"))
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_check_status: Mapped[str] = mapped_column(String(20), default="pending")

    lines = relationship("GoodsReceiptLine", back_populates="goods_receipt", lazy="selectin")

    __table_args__ = (
        Index("ix_grn_org_number", "org_id", "grn_number", unique=True),
    )


class GoodsReceiptLine(Base):
    """GRN line item."""
    __tablename__ = "goods_receipt_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    grn_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("goods_receipts.id"))
    po_line_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_order_lines.id"))
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    quantity_accepted: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    quantity_rejected: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    goods_receipt = relationship("GoodsReceipt", back_populates="lines")


class InvoiceMatch(Base, TimestampMixin, OrgScopedMixin):
    """Three-way match: PO ↔ GRN ↔ Invoice."""
    __tablename__ = "invoice_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"))
    po_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"))
    grn_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("goods_receipts.id"), nullable=True)
    match_status: Mapped[str] = mapped_column(String(20), nullable=False)  # matched / quantity_mismatch / price_mismatch / pending_grn
    quantity_match: Mapped[bool] = mapped_column(Boolean, default=False)
    price_match: Mapped[bool] = mapped_column(Boolean, default=False)
    tax_match: Mapped[bool] = mapped_column(Boolean, default=False)
    variance_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    variance_details: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
