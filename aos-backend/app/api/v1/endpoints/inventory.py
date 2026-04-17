"""Inventory API — stock queries, movements, reorder suggestions."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import AuthUser, DbSession, get_current_user
from app.models.inventory import MovementType
from app.services._base import DomainError
from app.services.inventory import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _svc(db, user: AuthUser) -> InventoryService:
    return InventoryService(db=db, org_id=uuid.UUID(str(user.org_id)))


@router.get("/stock/{product_id}")
async def get_stock(
    product_id: uuid.UUID,
    db: DbSession,
    warehouse_id: Optional[uuid.UUID] = None,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    return await _svc(db, user).get_stock(product_id, warehouse_id)


class MovementCreate(BaseModel):
    movement_type: MovementType
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal
    movement_date: Optional[date] = None
    unit_cost: Optional[Decimal] = None
    batch_number: Optional[str] = None
    serial_number: Optional[str] = None
    expiry_date: Optional[date] = None
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    source_warehouse_id: Optional[uuid.UUID] = None
    destination_warehouse_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


@router.post("/movements", status_code=status.HTTP_201_CREATED)
async def record_movement(
    req: MovementCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        m = await _svc(db, user).record_movement(
            performed_by=uuid.UUID(str(user.user_id)),
            **req.model_dump(),
        )
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {
        "id": str(m.id),
        "movement_number": m.movement_number,
        "type": m.movement_type.value,
        "quantity": str(m.quantity),
    }


@router.get("/reorder-suggestions")
async def reorder_suggestions(
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await _svc(db, user).reorder_suggestions()
