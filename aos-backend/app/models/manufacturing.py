"""
AOS Manufacturing Models
Bill of Materials, Production Orders, Work Centers, MRP.
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


class ProductionStatus(str, enum.Enum):
    PLANNED = "planned"
    RELEASED = "released"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class BillOfMaterials(Base, TimestampMixin, OrgScopedMixin):
    """BOM header — a production recipe."""
    __tablename__ = "bills_of_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    bom_number: Mapped[str] = mapped_column(String(50), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    output_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("1.000"))
    uom: Mapped[str] = mapped_column(String(20), default="NOS")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    estimated_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    scrap_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    operations: Mapped[dict] = mapped_column(JSON, default=list)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    lines = relationship("BOMLine", back_populates="bom", lazy="selectin")

    __table_args__ = (
        Index("ix_bom_org_product", "org_id", "product_id"),
        Index("ix_bom_org_number", "org_id", "bom_number", unique=True),
    )


class BOMLine(Base):
    """BOM component line — an ingredient in the recipe."""
    __tablename__ = "bom_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    bom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bills_of_materials.id"))
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    scrap_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)

    bom = relationship("BillOfMaterials", back_populates="lines")


class WorkCenter(Base, TimestampMixin, OrgScopedMixin):
    """Production work center / machine / line."""
    __tablename__ = "work_centers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True)
    capacity_per_hour: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 3), nullable=True)
    operating_hours: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("8.0"))
    hourly_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    current_status: Mapped[str] = mapped_column(String(20), default="available")  # available / busy / maintenance / breakdown
    maintenance_schedule: Mapped[dict] = mapped_column(JSON, default=list)

    __table_args__ = (
        Index("ix_wc_org_code", "org_id", "code", unique=True),
    )


class ProductionOrder(Base, TimestampMixin, OrgScopedMixin):
    """Production work order."""
    __tablename__ = "production_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    order_number: Mapped[str] = mapped_column(String(50), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    bom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bills_of_materials.id"))
    work_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("work_centers.id"), nullable=True)
    quantity_planned: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    quantity_produced: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))
    quantity_rejected: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0.000"))
    planned_start: Mapped[date] = mapped_column(Date, nullable=False)
    planned_end: Mapped[date] = mapped_column(Date, nullable=False)
    actual_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[ProductionStatus] = mapped_column(Enum(ProductionStatus), default=ProductionStatus.PLANNED)
    sales_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    supervisor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    material_availability: Mapped[dict] = mapped_column(JSON, default=dict)
    operations_log: Mapped[dict] = mapped_column(JSON, default=list)
    quality_check: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (
        Index("ix_po_mfg_org_number", "org_id", "order_number", unique=True),
    )
