"""
Inventory Service — stock levels, movements, reorder checks.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import (
    MovementType,
    Product,
    StockLevel,
    StockMovement,
    Warehouse,
)
from app.services._base import DomainError, DomainService


class InventoryService(DomainService):
    domain = "inventory"

    # ---- Stock lookups -----------------------------------------------------

    async def get_stock(
        self,
        product_id: uuid.UUID,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> dict[str, Any]:
        """Return stock summary for a product (all warehouses or one)."""
        stmt = select(StockLevel).where(
            and_(StockLevel.org_id == self.org_id, StockLevel.product_id == product_id)
        )
        if warehouse_id is not None:
            stmt = stmt.where(StockLevel.warehouse_id == warehouse_id)

        result = await self.db.execute(stmt)
        levels = list(result.scalars().all())

        on_hand = sum((l.quantity_on_hand or Decimal("0") for l in levels), Decimal("0"))
        reserved = sum((l.quantity_reserved or Decimal("0") for l in levels), Decimal("0"))
        on_order = sum((l.quantity_on_order or Decimal("0") for l in levels), Decimal("0"))
        available = on_hand - reserved

        return {
            "product_id": str(product_id),
            "warehouse_id": str(warehouse_id) if warehouse_id else None,
            "quantity_on_hand": str(on_hand),
            "quantity_reserved": str(reserved),
            "quantity_on_order": str(on_order),
            "available": str(available),
            "warehouses": [
                {
                    "warehouse_id": str(l.warehouse_id),
                    "on_hand": str(l.quantity_on_hand or Decimal("0")),
                    "reserved": str(l.quantity_reserved or Decimal("0")),
                }
                for l in levels
            ],
        }

    # ---- Stock movements ---------------------------------------------------

    async def record_movement(
        self,
        movement_type: MovementType,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        quantity: Decimal,
        performed_by: uuid.UUID,
        movement_date: Optional[date] = None,
        unit_cost: Optional[Decimal] = None,
        batch_number: Optional[str] = None,
        serial_number: Optional[str] = None,
        expiry_date: Optional[date] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        source_warehouse_id: Optional[uuid.UUID] = None,
        destination_warehouse_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> StockMovement:
        """
        Record a stock movement and update StockLevel atomically.

        Sign convention:
          RECEIPT / RETURN (from customer) => +qty to warehouse_id
          ISSUE / DAMAGE => -qty from warehouse_id
          ADJUSTMENT => delta (signed)
          TRANSFER => -qty from source, +qty to destination
        """
        qty = self._dec(quantity)
        if qty == 0:
            raise DomainError("Movement quantity cannot be zero", "zero_quantity")

        mdate = movement_date or date.today()
        mnumber = await self._next_movement_number()

        total_value = None
        if unit_cost is not None:
            total_value = (self._dec(unit_cost) * abs(qty)).quantize(Decimal("0.01"))

        movement = StockMovement(
            org_id=self.org_id,
            movement_number=mnumber,
            movement_type=movement_type,
            movement_date=mdate,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=qty,
            unit_cost=unit_cost,
            total_value=total_value,
            batch_number=batch_number,
            serial_number=serial_number,
            expiry_date=expiry_date,
            reference_type=reference_type,
            reference_id=reference_id,
            source_warehouse_id=source_warehouse_id,
            destination_warehouse_id=destination_warehouse_id,
            performed_by=performed_by,
            notes=notes,
        )
        self.db.add(movement)

        # Update stock levels
        if movement_type in (MovementType.RECEIPT, MovementType.RETURN):
            await self._adjust_level(product_id, warehouse_id, qty)
        elif movement_type in (MovementType.ISSUE, MovementType.DAMAGE):
            await self._adjust_level(product_id, warehouse_id, -qty)
        elif movement_type == MovementType.ADJUSTMENT:
            await self._adjust_level(product_id, warehouse_id, qty)
        elif movement_type == MovementType.TRANSFER:
            if source_warehouse_id is None or destination_warehouse_id is None:
                raise DomainError("Transfer requires source and destination", "invalid_transfer")
            await self._adjust_level(product_id, source_warehouse_id, -qty)
            await self._adjust_level(product_id, destination_warehouse_id, qty)

        await self.db.flush()
        return movement

    async def _adjust_level(
        self,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        delta: Decimal,
    ) -> StockLevel:
        result = await self.db.execute(
            select(StockLevel).where(
                and_(
                    StockLevel.product_id == product_id,
                    StockLevel.warehouse_id == warehouse_id,
                )
            )
        )
        level = result.scalars().first()
        if level is None:
            level = StockLevel(
                org_id=self.org_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_on_hand=Decimal("0"),
            )
            self.db.add(level)

        new_qty = (level.quantity_on_hand or Decimal("0")) + delta
        if new_qty < 0:
            raise DomainError(
                f"Insufficient stock: on hand {level.quantity_on_hand}, requested {-delta}",
                "insufficient_stock",
            )
        level.quantity_on_hand = new_qty
        level.last_movement_date = date.today()
        await self.db.flush()
        return level

    async def _next_movement_number(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"SM-{year}-"
        result = await self.db.execute(
            select(func.count(StockMovement.id)).where(
                and_(
                    StockMovement.org_id == self.org_id,
                    StockMovement.movement_number.like(f"{prefix}%"),
                )
            )
        )
        count = int(result.scalar() or 0) + 1
        return f"{prefix}{count:06d}"

    # ---- Reorder -----------------------------------------------------------

    async def reorder_suggestions(self) -> list[dict[str, Any]]:
        """Products at or below reorder level. Excludes inactive products."""
        stmt = (
            select(
                Product.id,
                Product.sku,
                Product.name,
                Product.reorder_level,
                Product.min_stock_level,
                Product.lead_time_days,
                Product.preferred_vendor_id,
                func.coalesce(func.sum(StockLevel.quantity_on_hand), 0).label("on_hand"),
                func.coalesce(func.sum(StockLevel.quantity_on_order), 0).label("on_order"),
            )
            .join(StockLevel, StockLevel.product_id == Product.id, isouter=True)
            .where(
                and_(
                    Product.org_id == self.org_id,
                    Product.is_active.is_(True),
                )
            )
            .group_by(
                Product.id,
                Product.sku,
                Product.name,
                Product.reorder_level,
                Product.min_stock_level,
                Product.lead_time_days,
                Product.preferred_vendor_id,
            )
        )
        result = await self.db.execute(stmt)
        suggestions = []
        for row in result.all():
            on_hand = self._dec(row.on_hand or 0)
            on_order = self._dec(row.on_order or 0)
            available_plus_pipeline = on_hand + on_order
            reorder_level = row.reorder_level or Decimal("0")
            if available_plus_pipeline <= reorder_level:
                target = max(reorder_level, (row.min_stock_level or Decimal("0")) * Decimal("2"))
                suggest_qty = (target - available_plus_pipeline).quantize(Decimal("0.001"))
                if suggest_qty > 0:
                    suggestions.append({
                        "product_id": str(row.id),
                        "sku": row.sku,
                        "name": row.name,
                        "on_hand": str(on_hand),
                        "on_order": str(on_order),
                        "reorder_level": str(reorder_level),
                        "suggested_quantity": str(suggest_qty),
                        "lead_time_days": row.lead_time_days,
                        "preferred_vendor_id": str(row.preferred_vendor_id) if row.preferred_vendor_id else None,
                    })
        return suggestions
