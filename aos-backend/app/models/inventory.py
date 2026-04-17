"""
AOS Inventory Models
Products, Warehouses, Stock Levels, Movements, Reorder Rules.
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


class MovementType(str, enum.Enum):
    RECEIPT = "receipt"           # Stock in (GRN)
    ISSUE = "issue"               # Stock out (sale, consumption)
    TRANSFER = "transfer"         # Warehouse to warehouse
    ADJUSTMENT = "adjustment"     # Cycle count correction
    DAMAGE = "damage"             # Damaged goods write-off
    RETURN = "return"             # Return from customer / to vendor


class Warehouse(Base, TimestampMixin, OrgScopedMixin):
    """Warehouse / stocking location master."""
    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("ix_wh_org_code", "org_id", "code", unique=True),
    )


class Product(Base, TimestampMixin, OrgScopedMixin):
    """Product / item / material master."""
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    uom: Mapped[str] = mapped_column(String(20), default="NOS")
    hsn_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"))
    standard_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    mrp: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    product_type: Mapped[str] = mapped_column(String(30), default="tradable")  # tradable / raw_material / finished_good / consumable / service
    is_batch_tracked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_serial_tracked: Mapped[bool] = mapped_column(Boolean, default=False)
    has_expiry: Mapped[bool] = mapped_column(Boolean, default=False)
    shelf_life_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)
    min_stock_level: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))
    max_stock_level: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 3), nullable=True)
    preferred_vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (
        Index("ix_products_org_sku", "org_id", "sku", unique=True),
        Index("ix_products_org_name", "org_id", "name"),
    )


class StockLevel(Base, TimestampMixin, OrgScopedMixin):
    """Current stock position per product per warehouse."""
    __tablename__ = "stock_levels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"))
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))
    quantity_reserved: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))
    quantity_on_order: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))
    avg_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    last_movement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    __table_args__ = (
        Index("ix_sl_product_wh", "product_id", "warehouse_id", unique=True),
        Index("ix_sl_org_product", "org_id", "product_id"),
    )


class StockMovement(Base, TimestampMixin, OrgScopedMixin):
    """Immutable log of all stock movements."""
    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    movement_number: Mapped[str] = mapped_column(String(50), nullable=False)
    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    total_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # grn / sale / transfer / cycle_count
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True)
    destination_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True)
    performed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_sm_org_date", "org_id", "movement_date"),
        Index("ix_sm_product_date", "product_id", "movement_date"),
    )


class ReorderRule(Base, TimestampMixin, OrgScopedMixin):
    """Reorder policy per product-warehouse combination."""
    __tablename__ = "reorder_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"))
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    reorder_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    safety_stock: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))
    auto_reorder: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    seasonal_adjustments: Mapped[dict] = mapped_column(JSON, default=dict)


class CycleCount(Base, TimestampMixin, OrgScopedMixin):
    """Physical inventory count sessions."""
    __tablename__ = "cycle_counts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    count_number: Mapped[str] = mapped_column(String(50), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"))
    count_date: Mapped[date] = mapped_column(Date, nullable=False)
    counted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    total_variance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    items_counted: Mapped[dict] = mapped_column(JSON, default=list)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
