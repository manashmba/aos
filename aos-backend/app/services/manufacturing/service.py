"""
Manufacturing Service — BOM, production orders, material availability.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, select

from app.models.inventory import StockLevel
from app.models.manufacturing import (
    BillOfMaterials,
    BOMLine,
    ProductionOrder,
    ProductionStatus,
    WorkCenter,
)
from app.services._base import DomainError, DomainService


class ManufacturingService(DomainService):
    domain = "manufacturing"

    # ---- BOM ---------------------------------------------------------------

    async def create_bom(
        self,
        product_id: uuid.UUID,
        components: list[dict[str, Any]],
        bom_number: Optional[str] = None,
        version: str = "1.0",
        output_quantity: Decimal = Decimal("1.000"),
        uom: str = "NOS",
        effective_from: Optional[date] = None,
        scrap_percent: Decimal = Decimal("0.00"),
        notes: Optional[str] = None,
    ) -> BillOfMaterials:
        if not components:
            raise DomainError("BOM must have at least one component", "empty_bom")

        bnum = bom_number or await self._next_bom_number()
        bom = BillOfMaterials(
            org_id=self.org_id,
            bom_number=bnum,
            product_id=product_id,
            version=version,
            output_quantity=self._dec(output_quantity),
            uom=uom,
            effective_from=effective_from or date.today(),
            scrap_percent=scrap_percent,
            is_active=True,
            notes=notes,
        )
        self.db.add(bom)
        await self.db.flush()

        for i, c in enumerate(components, start=1):
            self.db.add(BOMLine(
                bom_id=bom.id,
                line_number=i,
                component_id=c["component_id"],
                quantity=self._dec(c["quantity"]),
                uom=c.get("uom", "NOS"),
                scrap_percent=self._dec(c.get("scrap_percent", 0)),
                is_critical=c.get("is_critical", False),
            ))

        await self.db.flush()
        return bom

    async def _next_bom_number(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"BOM-{year}-"
        result = await self.db.execute(
            select(func.count(BillOfMaterials.id)).where(
                and_(
                    BillOfMaterials.org_id == self.org_id,
                    BillOfMaterials.bom_number.like(f"{prefix}%"),
                )
            )
        )
        count = int(result.scalar() or 0) + 1
        return f"{prefix}{count:04d}"

    # ---- Production Orders -------------------------------------------------

    async def check_material_availability(
        self,
        bom_id: uuid.UUID,
        quantity_planned: Decimal,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> dict[str, Any]:
        """Check if all BOM components are available for the planned output."""
        bom = await self.db.get(BillOfMaterials, bom_id)
        if bom is None or bom.org_id != self.org_id:
            raise DomainError("BOM not found", "not_found")

        # Fetch BOM lines
        result = await self.db.execute(
            select(BOMLine).where(BOMLine.bom_id == bom_id)
        )
        lines = list(result.scalars().all())
        if not lines:
            raise DomainError("BOM has no components", "empty_bom")

        ratio = self._dec(quantity_planned) / (bom.output_quantity or Decimal("1"))

        shortfalls: list[dict[str, Any]] = []
        all_available = True
        for line in lines:
            required = (line.quantity * ratio * (Decimal("1") + line.scrap_percent / Decimal("100"))).quantize(Decimal("0.0001"))

            stock_stmt = select(func.coalesce(func.sum(StockLevel.quantity_on_hand - StockLevel.quantity_reserved), 0)).where(
                StockLevel.product_id == line.component_id
            )
            if warehouse_id is not None:
                stock_stmt = stock_stmt.where(StockLevel.warehouse_id == warehouse_id)
            stock_result = await self.db.execute(stock_stmt)
            available = self._dec(stock_result.scalar() or 0)

            if available < required:
                all_available = False
                shortfalls.append({
                    "component_id": str(line.component_id),
                    "required": str(required),
                    "available": str(available),
                    "shortfall": str(required - available),
                    "is_critical": line.is_critical,
                })

        return {
            "bom_id": str(bom_id),
            "can_produce": all_available,
            "planned_quantity": str(quantity_planned),
            "shortfalls": shortfalls,
        }

    async def create_production_order(
        self,
        bom_id: uuid.UUID,
        quantity_planned: Decimal,
        planned_start: date,
        planned_end: date,
        created_by: uuid.UUID,
        work_center_id: Optional[uuid.UUID] = None,
        sales_order_id: Optional[uuid.UUID] = None,
        priority: str = "normal",
        enforce_material_availability: bool = True,
    ) -> ProductionOrder:
        bom = await self.db.get(BillOfMaterials, bom_id)
        if bom is None or bom.org_id != self.org_id:
            raise DomainError("BOM not found", "not_found")
        if planned_end < planned_start:
            raise DomainError("planned_end must be >= planned_start", "invalid_dates")

        availability = await self.check_material_availability(bom_id, quantity_planned)
        if enforce_material_availability and not availability["can_produce"]:
            critical_short = [s for s in availability["shortfalls"] if s["is_critical"]]
            if critical_short:
                raise DomainError(
                    f"Critical components short: {[s['component_id'] for s in critical_short]}",
                    "material_shortage",
                )

        order_number = await self._next_production_number()
        order = ProductionOrder(
            org_id=self.org_id,
            order_number=order_number,
            product_id=bom.product_id,
            bom_id=bom_id,
            work_center_id=work_center_id,
            quantity_planned=self._dec(quantity_planned),
            planned_start=planned_start,
            planned_end=planned_end,
            status=ProductionStatus.PLANNED,
            sales_order_id=sales_order_id,
            priority=priority,
            created_by=created_by,
            material_availability=availability,
        )
        self.db.add(order)
        await self.db.flush()
        return order

    async def release_production_order(
        self,
        order_id: uuid.UUID,
    ) -> ProductionOrder:
        po = await self.db.get(ProductionOrder, order_id)
        if po is None or po.org_id != self.org_id:
            raise DomainError("Production order not found", "not_found")
        if po.status != ProductionStatus.PLANNED:
            raise DomainError(f"Cannot release order in state {po.status.value}", "invalid_state")
        po.status = ProductionStatus.RELEASED
        po.actual_start = date.today()
        await self.db.flush()
        return po

    async def _next_production_number(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"WO-{year}-"
        result = await self.db.execute(
            select(func.count(ProductionOrder.id)).where(
                and_(
                    ProductionOrder.org_id == self.org_id,
                    ProductionOrder.order_number.like(f"{prefix}%"),
                )
            )
        )
        count = int(result.scalar() or 0) + 1
        return f"{prefix}{count:05d}"
