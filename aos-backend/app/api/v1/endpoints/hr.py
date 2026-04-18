"""HR API — employees, leave, reimbursement."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import AuthUser, DbSession, get_current_user
from app.services._base import DomainError
from app.services.hr import HRService

router = APIRouter(prefix="/hr", tags=["hr"])


def _svc(db, user: AuthUser) -> HRService:
    return HRService(db=db, org_id=uuid.UUID(str(user.org_id)))


class EmployeeCreate(BaseModel):
    employee_code: str
    name: str
    date_of_joining: date
    department: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    ctc: Optional[Decimal] = None
    basic: Optional[Decimal] = None
    pan: Optional[str] = None
    aadhar: Optional[str] = None
    pf_number: Optional[str] = None
    esi_number: Optional[str] = None
    reporting_manager_id: Optional[uuid.UUID] = None


@router.post("/employees", status_code=status.HTTP_201_CREATED)
async def onboard_employee(
    req: EmployeeCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        e = await _svc(db, user).onboard_employee(**req.model_dump())
        await db.commit()
    except DomainError as ex:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": ex.code, "message": str(ex)})
    return {
        "id": str(e.id),
        "employee_code": e.employee_code,
        "name": e.name,
        "status": e.status.value,
    }


class LeaveApply(BaseModel):
    employee_id: uuid.UUID
    leave_type: str
    from_date: date
    to_date: date
    reason: Optional[str] = None


@router.post("/leaves", status_code=status.HTTP_201_CREATED)
async def apply_leave(
    req: LeaveApply,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        lr = await _svc(db, user).apply_leave(**req.model_dump())
        await db.commit()
    except DomainError as ex:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": ex.code, "message": str(ex)})
    return {
        "id": str(lr.id),
        "request_number": lr.request_number,
        "days": str(lr.days),
        "status": lr.status,
    }


class LeaveApprove(BaseModel):
    notes: Optional[str] = None


@router.post("/leaves/{leave_id}/approve")
async def approve_leave(
    leave_id: uuid.UUID,
    req: LeaveApprove,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        lr = await _svc(db, user).approve_leave(
            leave_id, uuid.UUID(str(user.user_id)), notes=req.notes
        )
        await db.commit()
    except DomainError as ex:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": ex.code, "message": str(ex)})
    return {"id": str(lr.id), "status": lr.status}


class ReimbursementCreate(BaseModel):
    employee_id: uuid.UUID
    expense_date: date
    category: str
    description: str
    amount: Decimal
    receipt_url: Optional[str] = None
    project_code: Optional[str] = None


@router.post("/reimbursements", status_code=status.HTTP_201_CREATED)
async def submit_reimbursement(
    req: ReimbursementCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        r = await _svc(db, user).submit_reimbursement(**req.model_dump())
        await db.commit()
    except DomainError as ex:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": ex.code, "message": str(ex)})
    return {
        "id": str(r.id),
        "claim_number": r.claim_number,
        "amount": str(r.amount),
        "status": r.status,
    }
