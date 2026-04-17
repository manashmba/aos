"""
AOS Sales Models
Customers, Quotations, Sales Orders, Credit Management.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
import enum

from sqlalchemy import (
    Boolean, Date, Enum, ForeignKey, Index,
    Integer, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import OrgScopedMixin, TimestampMixin, generate_uuid


class CustomerStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    BLACKLISTED = "blacklisted"
    INACTIVE = "inactive"


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    CONFIRMED = "confirmed"
    PARTIALLY_DISPATCHED = "partially_dispatched"
    FULLY_DISPATCHED = "fully_dispatched"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Customer(Base, TimestampMixin, OrgScopedMixin):
    """Customer master."""
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pan: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    billing_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shipping_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_type: Mapped[str] = mapped_column(String(20), default="b2b")  # b2b / b2c / export
    status: Mapped[CustomerStatus] = mapped_column(Enum(CustomerStatus), default=CustomerStatus.PENDING)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    credit_days: Mapped[int] = mapped_column(Integer, default=30)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    price_list: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sales_rep_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    segment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tcs_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (
        Index("ix_customers_org_code", "org_id", "code", unique=True),
        Index("ix_customers_org_name", "org_id", "name"),
    )


class Quotation(Base, TimestampMixin, OrgScopedMixin):
    """Sales quotation."""
    __tablename__ = "quotations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    quote_number: Mapped[str] = mapped_column(String(50), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"))
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft / sent / accepted / rejected / expired
    terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    line_items: Mapped[dict] = mapped_column(JSON, default=list)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    so_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)

    __table_args__ = (
        Index("ix_quotes_org_number", "org_id", "quote_number", unique=True),
    )


class SalesOrder(Base, TimestampMixin, OrgScopedMixin):
    """Sales order header."""
    __tablename__ = "sales_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    so_number: Mapped[str] = mapped_column(String(50), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"))
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_dispatch: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_delivery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    shipping_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.DRAFT)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)
    credit_check_status: Mapped[str] = mapped_column(String(20), default="pending")
    credit_risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    special_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quotation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("quotations.id"), nullable=True)

    # Relationships
    lines = relationship("SalesOrderLine", back_populates="sales_order", lazy="selectin")
    customer = relationship("Customer", lazy="selectin")

    __table_args__ = (
        Index("ix_so_org_number", "org_id", "so_number", unique=True),
        Index("ix_so_org_status", "org_id", "status"),
        Index("ix_so_org_customer", "org_id", "customer_id"),
    )


class SalesOrderLine(Base):
    """Sales order line item."""
    __tablename__ = "sales_order_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    so_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_orders.id"))
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), default="NOS")
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    hsn_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    dispatched_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))

    sales_order = relationship("SalesOrder", back_populates="lines")


class CustomerCredit(Base, TimestampMixin, OrgScopedMixin):
    """Customer credit exposure tracking."""
    __tablename__ = "customer_credits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), unique=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    current_outstanding: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    pending_orders_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    available_credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    overdue_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    aging_current: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    aging_1_30: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    aging_31_60: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    aging_61_90: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    aging_over_90: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    last_payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_assessment: Mapped[dict] = mapped_column(JSON, default=dict)
