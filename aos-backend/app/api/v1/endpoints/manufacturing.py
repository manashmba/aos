"""Manufacturing API — BOM, material availability, production orders."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import AuthUser, DbSession, get_current_user
from app.services._base import DomainError
from app.services.manufacturing import ManufacturingService

router = APIRouter(prefix="/manufacturing", tags=["manufacturing"])


def _svc(db, user: AuthUser) -> ManufacturingService:
    return ManufacturingService(db=db, org_id=uuid.UUID(str(user.org_id)))


class BOMComponentIn(BaseModel):
    component_id: uuid.UUID
    quantity: Decimal
    uom: str = "NOS"
    scrap_percent: Decimal = Decimal("0")
    is_critical: bool = False


class BOMCreate(BaseModel):
    product_id: uuid.UUID
    components: list[BOMComponentIn] = Field(min_length=1)
    bom_number: Optional[str] = None
    version: str = "1.0"
    output_quantity: Decimal = Decimal("1.000")
    uom: str = "NOS"
    effective_from: Optional[date] = None
    scrap_percent: Decimal = Decimal("0.00")
    notes: Optional[str] = None


@router.post("/boms", status_code=status.HTTP_201_CREATED)
async def create_bom(
    req: BOMCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        bom = await _svc(db, user).create_bom(
            product_id=req.product_id,
            components=[c.model_dump() for c in req.components],
            bom_number=req.bom_number,
            version=req.version,
            output_quantity=req.output_quantity,
            uom=req.uom,
            effective_from=req.effective_from,
            scrap_percent=req.scrap_percent,
            notes=req.notes,
        )
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {"id": str(bom.id), "bom_number": bom.bom_number, "version": bom.version}


@router.get("/boms/{bom_id}/availability")
async def check_availability(
    bom_id: uuid.UUID,
    quantity_planned: Decimal,
    db: DbSession,
    warehouse_id: Optional[uuid.UUID] = None,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return await _svc(db, user).check_material_availability(
            bom_id, quantity_planned, warehouse_id
        )
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})


class ProductionOrderCreate(BaseModel):
    bom_id: uuid.UUID
    quantity_planned: Decimal
    planned_start: date
    planned_end: date
    work_center_id: Optional[uuid.UUID] = None
    sales_order_id: Optional[uuid.UUID] = None
    priority: str = "normal"
    enforce_material_availability: bool = True


@router.post("/production-orders", status_code=status.HTTP_201_CREATED)
async def create_production_order(
    req: ProductionOrderCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        po = await _svc(db, user).create_production_order(
            created_by=uuid.UUID(str(user.user_id)),
            **req.model_dump(),
        )
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {
        "id": str(po.id),
        "order_number": po.order_number,
        "status": po.status.value,
        "quantity_planned": str(po.quantity_planned),
    }


@router.post("/production-orders/{order_id}/release")
async def release_production_order(
    order_id: uuid.UUID,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        po = await _svc(db, user).release_production_order(order_id)
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {"id": str(po.id), "status": po.status.value}
