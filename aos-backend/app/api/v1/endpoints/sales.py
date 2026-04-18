"""Sales API — customers, credit status, sales orders."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import AuthUser, DbSession, get_current_user
from app.services._base import DomainError
from app.services.sales import SalesService

router = APIRouter(prefix="/sales", tags=["sales"])


def _svc(db, user: AuthUser) -> SalesService:
    return SalesService(db=db, org_id=uuid.UUID(str(user.org_id)))


class CustomerCreate(BaseModel):
    code: str
    name: str
    credit_limit: Decimal = Decimal("0.00")
    credit_days: int = 30
    gstin: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


@router.post("/customers", status_code=status.HTTP_201_CREATED)
async def onboard_customer(
    req: CustomerCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        c = await _svc(db, user).onboard_customer(**req.model_dump())
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {"id": str(c.id), "code": c.code, "name": c.name, "status": c.status.value}


@router.get("/customers/{customer_id}/credit-status")
async def credit_status(
    customer_id: uuid.UUID,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return await _svc(db, user).credit_status(customer_id)
    except DomainError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": e.code, "message": str(e)})


class SOLineIn(BaseModel):
    product_id: uuid.UUID
    description: str
    quantity: Decimal
    rate: Decimal
    discount_percent: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("18")
    uom: str = "NOS"
    hsn_code: Optional[str] = None


class SalesOrderCreate(BaseModel):
    customer_id: uuid.UUID
    order_date: date
    lines: list[SOLineIn] = Field(min_length=1)
    expected_dispatch: Optional[date] = None
    expected_delivery: Optional[date] = None
    warehouse_id: Optional[uuid.UUID] = None
    payment_terms_days: Optional[int] = None
    special_instructions: Optional[str] = None
    quotation_id: Optional[uuid.UUID] = None


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    req: SalesOrderCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        so = await _svc(db, user).create_sales_order(
            customer_id=req.customer_id,
            order_date=req.order_date,
            lines=[l.model_dump() for l in req.lines],
            created_by=uuid.UUID(str(user.user_id)),
            expected_dispatch=req.expected_dispatch,
            expected_delivery=req.expected_delivery,
            warehouse_id=req.warehouse_id,
            payment_terms_days=req.payment_terms_days,
            special_instructions=req.special_instructions,
            quotation_id=req.quotation_id,
        )
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {
        "id": str(so.id),
        "so_number": so.so_number,
        "status": so.status.value,
        "total_amount": str(so.total_amount),
        "credit_check_status": so.credit_check_status,
    }


@router.post("/orders/{so_id}/approve")
async def approve_sales_order(
    so_id: uuid.UUID,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        so = await _svc(db, user).approve_sales_order(so_id, uuid.UUID(str(user.user_id)))
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {"id": str(so.id), "status": so.status.value}
