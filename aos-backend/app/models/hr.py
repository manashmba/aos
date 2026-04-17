"""
AOS HR Models
Employees, Leave, Reimbursements, Attendance.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import enum

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Index,
    Integer, Numeric, String, Text, Time,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OrgScopedMixin, TimestampMixin, generate_uuid


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    PROBATION = "probation"
    NOTICE_PERIOD = "notice_period"
    SEPARATED = "separated"


class Employee(Base, TimestampMixin, OrgScopedMixin):
    """Employee master."""
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    employee_code: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    date_of_joining: Mapped[date] = mapped_column(Date, nullable=False)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_of_separation: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    reporting_manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[EmployeeStatus] = mapped_column(Enum(EmployeeStatus), default=EmployeeStatus.ACTIVE)
    ctc: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    basic: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    pan: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    aadhar: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    pf_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    esi_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bank_account: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    leave_balance: Mapped[dict] = mapped_column(JSON, default=dict)
    addresses: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (
        Index("ix_emp_org_code", "org_id", "employee_code", unique=True),
    )


class LeaveRequest(Base, TimestampMixin, OrgScopedMixin):
    """Employee leave request."""
    __tablename__ = "leave_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    request_number: Mapped[str] = mapped_column(String(50), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"))
    leave_type: Mapped[str] = mapped_column(String(30), nullable=False)  # casual / sick / privileged / comp_off / unpaid
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / approved / rejected / cancelled
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Reimbursement(Base, TimestampMixin, OrgScopedMixin):
    """Expense reimbursement claim."""
    __tablename__ = "reimbursements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    claim_number: Mapped[str] = mapped_column(String(50), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"))
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # travel / meals / accommodation / office / other
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    receipt_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    project_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / approved / rejected / paid
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_reim_org_number", "org_id", "claim_number", unique=True),
    )


class AttendanceRecord(Base, TimestampMixin, OrgScopedMixin):
    """Daily attendance log."""
    __tablename__ = "attendance_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"))
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    hours_worked: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="present")  # present / absent / leave / holiday / weekoff / half_day
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_att_emp_date", "employee_id", "attendance_date", unique=True),
    )
