"""
HR Service — employee onboarding, leave, reimbursement, attendance.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, select

from app.models.hr import (
    AttendanceRecord,
    Employee,
    EmployeeStatus,
    LeaveRequest,
    Reimbursement,
)
from app.services._base import DomainError, DomainService


_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_AADHAR_RE = re.compile(r"^[0-9]{12}$")


class HRService(DomainService):
    domain = "hr"

    # ---- Onboarding --------------------------------------------------------

    async def onboard_employee(
        self,
        employee_code: str,
        name: str,
        date_of_joining: date,
        department: Optional[str] = None,
        designation: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        ctc: Optional[Decimal] = None,
        basic: Optional[Decimal] = None,
        pan: Optional[str] = None,
        aadhar: Optional[str] = None,
        pf_number: Optional[str] = None,
        esi_number: Optional[str] = None,
        reporting_manager_id: Optional[uuid.UUID] = None,
        **extra: Any,
    ) -> Employee:
        if pan and not _PAN_RE.match(pan):
            raise DomainError(f"Invalid PAN format: {pan}", "invalid_pan")
        if aadhar and not _AADHAR_RE.match(aadhar):
            raise DomainError("Aadhar must be 12 digits", "invalid_aadhar")

        emp = Employee(
            org_id=self.org_id,
            employee_code=employee_code,
            name=name,
            date_of_joining=date_of_joining,
            department=department,
            designation=designation,
            email=email,
            phone=phone,
            ctc=ctc,
            basic=basic,
            pan=pan,
            aadhar=aadhar,
            pf_number=pf_number,
            esi_number=esi_number,
            reporting_manager_id=reporting_manager_id,
            status=EmployeeStatus.PROBATION,
            leave_balance={"casual": 12, "sick": 12, "privileged": 18},
        )
        self.db.add(emp)
        await self.db.flush()
        return emp

    # ---- Leave -------------------------------------------------------------

    async def apply_leave(
        self,
        employee_id: uuid.UUID,
        leave_type: str,
        from_date: date,
        to_date: date,
        reason: Optional[str] = None,
    ) -> LeaveRequest:
        if to_date < from_date:
            raise DomainError("to_date must be on or after from_date", "invalid_dates")

        emp = await self.db.get(Employee, employee_id)
        if emp is None or emp.org_id != self.org_id:
            raise DomainError("Employee not found", "not_found")

        days = Decimal((to_date - from_date).days + 1)

        # Check leave balance (soft check for paid leave types)
        balance = (emp.leave_balance or {}).get(leave_type)
        if balance is not None and Decimal(str(balance)) < days and leave_type != "unpaid":
            raise DomainError(
                f"Insufficient {leave_type} leave balance: {balance} days remaining, {days} requested",
                "insufficient_balance",
            )

        req_number = await self._next_leave_number()
        lr = LeaveRequest(
            org_id=self.org_id,
            request_number=req_number,
            employee_id=employee_id,
            leave_type=leave_type,
            from_date=from_date,
            to_date=to_date,
            days=days,
            reason=reason,
            status="pending",
        )
        self.db.add(lr)
        await self.db.flush()
        return lr

    async def approve_leave(
        self,
        leave_id: uuid.UUID,
        approved_by: uuid.UUID,
        notes: Optional[str] = None,
    ) -> LeaveRequest:
        lr = await self.db.get(LeaveRequest, leave_id)
        if lr is None or lr.org_id != self.org_id:
            raise DomainError("Leave request not found", "not_found")
        if lr.status != "pending":
            raise DomainError(f"Leave already {lr.status}", "invalid_state")
        lr.status = "approved"
        lr.approved_by = approved_by
        lr.approval_notes = notes

        # Deduct from balance
        emp = await self.db.get(Employee, lr.employee_id)
        if emp is not None and lr.leave_type != "unpaid":
            bal = dict(emp.leave_balance or {})
            remaining = Decimal(str(bal.get(lr.leave_type, 0))) - lr.days
            bal[lr.leave_type] = float(max(Decimal("0"), remaining))
            emp.leave_balance = bal

        await self.db.flush()
        return lr

    async def _next_leave_number(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"LV-{year}-"
        result = await self.db.execute(
            select(func.count(LeaveRequest.id)).where(
                and_(
                    LeaveRequest.org_id == self.org_id,
                    LeaveRequest.request_number.like(f"{prefix}%"),
                )
            )
        )
        count = int(result.scalar() or 0) + 1
        return f"{prefix}{count:06d}"

    # ---- Reimbursement -----------------------------------------------------

    async def submit_reimbursement(
        self,
        employee_id: uuid.UUID,
        expense_date: date,
        category: str,
        description: str,
        amount: Decimal,
        receipt_url: Optional[str] = None,
        project_code: Optional[str] = None,
    ) -> Reimbursement:
        if amount <= 0:
            raise DomainError("Amount must be positive", "invalid_amount")
        emp = await self.db.get(Employee, employee_id)
        if emp is None or emp.org_id != self.org_id:
            raise DomainError("Employee not found", "not_found")

        claim_number = await self._next_reimb_number()
        r = Reimbursement(
            org_id=self.org_id,
            claim_number=claim_number,
            employee_id=employee_id,
            expense_date=expense_date,
            category=category,
            description=description,
            amount=self._dec(amount),
            receipt_url=receipt_url,
            project_code=project_code,
            status="pending",
        )
        self.db.add(r)
        await self.db.flush()
        return r

    async def _next_reimb_number(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"REIMB-{year}-"
        result = await self.db.execute(
            select(func.count(Reimbursement.id)).where(
                and_(
                    Reimbursement.org_id == self.org_id,
                    Reimbursement.claim_number.like(f"{prefix}%"),
                )
            )
        )
        count = int(result.scalar() or 0) + 1
        return f"{prefix}{count:06d}"
