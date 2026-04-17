"""Finance API — accounts, journal entries, invoices, payments, trial balance."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import AuthUser, DbSession, get_current_user
from app.models.finance import AccountType, InvoiceType
from app.services._base import DomainError
from app.services.finance import FinanceService

router = APIRouter(prefix="/finance", tags=["finance"])


def _svc(db, user: AuthUser) -> FinanceService:
    return FinanceService(db=db, org_id=uuid.UUID(str(user.org_id)))


# ---- Accounts --------------------------------------------------------------

class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: AccountType
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    currency: str = "INR"


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def create_account(
    req: AccountCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        acct = await _svc(db, user).create_account(**req.model_dump())
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {"id": str(acct.id), "code": acct.code, "name": acct.name}


# ---- Journal Entries -------------------------------------------------------

class JournalLineIn(BaseModel):
    account_id: uuid.UUID
    debit: Decimal = Field(default=Decimal("0.00"))
    credit: Decimal = Field(default=Decimal("0.00"))
    description: Optional[str] = None
    cost_center: Optional[str] = None


class JournalEntryCreate(BaseModel):
    description: str
    lines: list[JournalLineIn]
    entry_date: Optional[date] = None
    idempotency_key: str
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None


@router.post("/journal-entries", status_code=status.HTTP_201_CREATED)
async def post_journal(
    req: JournalEntryCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        je = await _svc(db, user).post_journal_entry(
            description=req.description,
            lines=[l.model_dump() for l in req.lines],
            posted_by=uuid.UUID(str(user.user_id)),
            idempotency_key=req.idempotency_key,
            entry_date=req.entry_date,
            reference_type=req.reference_type,
            reference_id=req.reference_id,
        )
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {
        "id": str(je.id),
        "entry_number": je.entry_number,
        "entry_date": je.entry_date.isoformat(),
        "fiscal_year": je.fiscal_year,
    }


@router.get("/trial-balance")
async def trial_balance(
    db: DbSession,
    as_of: Optional[date] = None,
    user: AuthUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await _svc(db, user).trial_balance(as_of=as_of)


@router.get("/ageing")
async def ageing(
    db: DbSession,
    invoice_type: InvoiceType = InvoiceType.SALES,
    as_of: Optional[date] = None,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    buckets = await _svc(db, user).ageing_buckets(as_of=as_of, invoice_type=invoice_type)
    return {k: str(v) for k, v in buckets.items()}


# ---- Payments --------------------------------------------------------------

class PaymentCreate(BaseModel):
    payment_type: str = Field(..., pattern="^(inbound|outbound)$")
    payment_mode: str
    amount: Decimal
    payment_date: date
    idempotency_key: str
    vendor_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    invoice_id: Optional[uuid.UUID] = None
    tds_amount: Decimal = Decimal("0.00")
    tds_section: Optional[str] = None
    notes: Optional[str] = None


@router.post("/payments", status_code=status.HTTP_201_CREATED)
async def create_payment(
    req: PaymentCreate,
    db: DbSession,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        pay = await _svc(db, user).create_payment(**req.model_dump())
        await db.commit()
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": e.code, "message": str(e)})
    return {
        "id": str(pay.id),
        "payment_number": pay.payment_number,
        "status": pay.status.value,
        "amount": str(pay.amount),
    }
