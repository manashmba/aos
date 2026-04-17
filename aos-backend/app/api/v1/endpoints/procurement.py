"""Procurement API — vendors, purchase orders, GRN, three-way match."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import AuthUser, DbSession, get_current_user
from app.services._base import DomainError
from app.services.procurement import ProcurementService

router = APIRouter(prefix="/procurement", tags=["procurement"])


def _svc(db, user: AuthUser) -> ProcurementService:
    return ProcurementService(db=db, org_id=uuid.UUID(str(user.org_id)))


# ---- Vendor schemas --------------------------------------------------------

class VendorCreate(BaseModel):
    code: str
    name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    payment_terms_days: int = 30
    tds_applicable: bool = False
    tds_rate: Decimal = Decimal("0.00")
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


@router.post("/vendors", status_code=status.HTTP_201_CREATED)
async def onboard_vendor(
    req: VendorCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        vendor = await _svc(db, user).onboard_vendor(**req.model_dump())
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {"id": str(vendor.id), "code": vendor.code, "status": vendor.status.value}


@router.post("/vendors/{vendor_id}/approve")
async def approve_vendor(
    vendor_id: uuid.UUID,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        v = await _svc(db, user).approve_vendor(vendor_id, uuid.UUID(str(user.user_id)))
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return {"id": str(v.id), "status": v.status.value}


# ---- PO schemas ------------------------------------------------------------

class POLineIn(BaseModel):
    description: str
    quantity: Decimal
    rate: Decimal
    uom: str = "NOS"
    tax_rate: Decimal = Decimal("18.0")
    hsn_code: Optional[str] = None
    product_id: Optional[uuid.UUID] = None


class POCreate(BaseModel):
    vendor_id: uuid.UUID
    order_date: date
    expected_delivery: Optional[date] = None
    delivery_location: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    lines: list[POLineIn]


@router.post("/purchase-orders", status_code=status.HTTP_201_CREATED)
async def create_po(
    req: POCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        po = await _svc(db, user).create_po(
            vendor_id=req.vendor_id,
            order_date=req.order_date,
            lines=[l.model_dump() for l in req.lines],
            created_by=uuid.UUID(str(user.user_id)),
            expected_delivery=req.expected_delivery,
            delivery_location=req.delivery_location,
            warehouse_id=req.warehouse_id,
            payment_terms=req.payment_terms,
            notes=req.notes,
        )
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {
        "id": str(po.id),
        "po_number": po.po_number,
        "total_amount": str(po.total_amount),
        "status": po.status.value,
    }


@router.post("/purchase-orders/{po_id}/approve")
async def approve_po(
    po_id: uuid.UUID,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        po = await _svc(db, user).approve_po(po_id, uuid.UUID(str(user.user_id)))
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {"id": str(po.id), "status": po.status.value}


# ---- GRN schemas -----------------------------------------------------------

class GRNLineIn(BaseModel):
    po_line_id: uuid.UUID
    quantity_received: Decimal
    quantity_accepted: Optional[Decimal] = None
    quantity_rejected: Decimal = Decimal("0")
    batch_number: Optional[str] = None
    rejection_reason: Optional[str] = None


class GRNCreate(BaseModel):
    po_id: uuid.UUID
    warehouse_id: uuid.UUID
    receipt_date: date
    notes: Optional[str] = None
    lines: list[GRNLineIn]


@router.post("/goods-receipts", status_code=status.HTTP_201_CREATED)
async def record_grn(
    req: GRNCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        grn = await _svc(db, user).record_grn(
            po_id=req.po_id,
            warehouse_id=req.warehouse_id,
            receipt_date=req.receipt_date,
            received_by=uuid.UUID(str(user.user_id)),
            lines=[l.model_dump() for l in req.lines],
            notes=req.notes,
        )
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {"id": str(grn.id), "grn_number": grn.grn_number, "status": grn.status}


# ---- Three-way match -------------------------------------------------------

class MatchRequest(BaseModel):
    invoice_id: uuid.UUID
    po_id: uuid.UUID
    grn_id: Optional[uuid.UUID] = None
    tolerance_pct: Decimal = Decimal("2.0")


@router.post("/match")
async def three_way_match(
    req: MatchRequest,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        m = await _svc(db, user).three_way_match(**req.model_dump())
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {
        "id": str(m.id),
        "status": m.match_status,
        "price_match": m.price_match,
        "quantity_match": m.quantity_match,
    }
