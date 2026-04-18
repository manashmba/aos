"""
Sales Service — customers, credit check, quotations, sales orders.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Invoice, InvoiceStatus, InvoiceType
from app.models.sales import (
    Customer,
    CustomerStatus,
    OrderStatus,
    SalesOrder,
    SalesOrderLine,
)
from app.services._base import DomainError, DomainService


class SalesService(DomainService):
    domain = "sales"

    # ---- Customers ---------------------------------------------------------

    async def onboard_customer(
        self,
        code: str,
        name: str,
        credit_limit: Decimal = Decimal("0.00"),
        credit_days: int = 30,
        gstin: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        **extra: Any,
    ) -> Customer:
        cust = Customer(
            org_id=self.org_id,
            code=code,
            name=name,
            gstin=gstin,
            phone=phone,
            email=email,
            credit_limit=credit_limit,
            credit_days=credit_days,
            status=CustomerStatus.PENDING,
            **{k: v for k, v in extra.items() if hasattr(Customer, k)},
        )
        self.db.add(cust)
        await self.db.flush()
        return cust

    # ---- Credit check ------------------------------------------------------

    async def credit_status(self, customer_id: uuid.UUID) -> dict[str, Any]:
        """Return customer's outstanding and whether they are within credit limit."""
        customer = await self.db.get(Customer, customer_id)
        if customer is None or customer.org_id != self.org_id:
            raise DomainError("Customer not found", "not_found")

        # Sum outstanding receivables
        result = await self.db.execute(
            select(func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0))
            .where(
                and_(
                    Invoice.org_id == self.org_id,
                    Invoice.customer_id == customer_id,
                    Invoice.invoice_type == InvoiceType.SALES,
                    Invoice.status.in_([
                        InvoiceStatus.POSTED,
                        InvoiceStatus.APPROVED,
                        InvoiceStatus.PARTIALLY_PAID,
                    ]),
                )
            )
        )
        outstanding = self._dec(result.scalar() or 0)

        # Overdue outstanding
        today = date.today()
        overdue_result = await self.db.execute(
            select(func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0))
            .where(
                and_(
                    Invoice.org_id == self.org_id,
                    Invoice.customer_id == customer_id,
                    Invoice.invoice_type == InvoiceType.SALES,
                    Invoice.due_date < today,
                    Invoice.status.in_([
                        InvoiceStatus.POSTED,
                        InvoiceStatus.APPROVED,
                        InvoiceStatus.PARTIALLY_PAID,
                    ]),
                )
            )
        )
        overdue = self._dec(overdue_result.scalar() or 0)

        credit_limit = customer.credit_limit or Decimal("0.00")
        available = credit_limit - outstanding

        return {
            "customer_id": str(customer_id),
            "credit_limit": str(credit_limit),
            "outstanding": str(outstanding),
            "overdue": str(overdue),
            "available": str(available),
            "within_limit": available >= 0,
            "has_overdue": overdue > 0,
            "status": customer.status.value,
        }

    # ---- Sales Orders ------------------------------------------------------

    async def create_sales_order(
        self,
        customer_id: uuid.UUID,
        order_date: date,
        lines: list[dict[str, Any]],
        created_by: uuid.UUID,
        expected_dispatch: Optional[date] = None,
        expected_delivery: Optional[date] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        payment_terms_days: Optional[int] = None,
        special_instructions: Optional[str] = None,
        quotation_id: Optional[uuid.UUID] = None,
    ) -> SalesOrder:
        if not lines:
            raise DomainError("Sales order must have at least one line", "empty_so")

        customer = await self.db.get(Customer, customer_id)
        if customer is None or customer.org_id != self.org_id:
            raise DomainError("Customer not found", "not_found")
        if customer.status == CustomerStatus.BLACKLISTED:
            raise DomainError("Customer is blacklisted", "blacklisted")
        if customer.status == CustomerStatus.ON_HOLD:
            raise DomainError("Customer is on hold", "on_hold")

        subtotal = Decimal("0.00")
        discount_total = Decimal("0.00")
        tax_total = Decimal("0.00")
        prepared: list[dict[str, Any]] = []
        for i, line in enumerate(lines, start=1):
            qty = self._dec(line["quantity"])
            rate = self._dec(line["rate"])
            discount_pct = self._dec(line.get("discount_percent", 0))
            gross = qty * rate
            disc_amt = (gross * discount_pct / Decimal("100")).quantize(Decimal("0.01"))
            amount = (gross - disc_amt).quantize(Decimal("0.01"))
            tax_rate = self._dec(line.get("tax_rate", 18))
            tax_amt = (amount * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
            subtotal += amount
            discount_total += disc_amt
            tax_total += tax_amt
            prepared.append({
                "line_number": i,
                "product_id": line["product_id"],
                "description": line["description"],
                "quantity": qty,
                "rate": rate,
                "discount_percent": discount_pct,
                "amount": amount,
                "uom": line.get("uom", "NOS"),
                "tax_rate": tax_rate,
                "tax_amount": tax_amt,
                "hsn_code": line.get("hsn_code"),
            })

        total = subtotal + tax_total

        # Credit check
        credit = await self.credit_status(customer_id)
        available = Decimal(credit["available"])
        exceeds_limit = available - total < 0

        so_number = await self._next_so_number()
        so = SalesOrder(
            org_id=self.org_id,
            so_number=so_number,
            customer_id=customer_id,
            order_date=order_date,
            expected_dispatch=expected_dispatch,
            expected_delivery=expected_delivery,
            warehouse_id=warehouse_id,
            subtotal=subtotal,
            discount_amount=discount_total,
            tax_amount=tax_total,
            total_amount=total,
            status=OrderStatus.PENDING_APPROVAL if exceeds_limit else OrderStatus.DRAFT,
            payment_terms_days=payment_terms_days or customer.credit_days or 30,
            credit_check_status="exceeded" if exceeds_limit else "ok",
            created_by=created_by,
            special_instructions=special_instructions,
            quotation_id=quotation_id,
        )
        self.db.add(so)
        await self.db.flush()

        for line in prepared:
            self.db.add(SalesOrderLine(so_id=so.id, **line))

        await self.db.flush()
        return so

    async def _next_so_number(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"SO-{year}-"
        result = await self.db.execute(
            select(func.count(SalesOrder.id)).where(
                and_(
                    SalesOrder.org_id == self.org_id,
                    SalesOrder.so_number.like(f"{prefix}%"),
                )
            )
        )
        count = int(result.scalar() or 0) + 1
        return f"{prefix}{count:05d}"

    async def approve_sales_order(
        self,
        so_id: uuid.UUID,
        approved_by: uuid.UUID,
    ) -> SalesOrder:
        so = await self.db.get(SalesOrder, so_id)
        if so is None or so.org_id != self.org_id:
            raise DomainError("Sales order not found", "not_found")
        if so.status not in (OrderStatus.DRAFT, OrderStatus.PENDING_APPROVAL):
            raise DomainError(f"SO cannot be approved in state {so.status.value}", "invalid_state")
        so.status = OrderStatus.APPROVED
        so.approved_by = approved_by
        await self.db.flush()
        return so
