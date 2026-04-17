"""
Procurement Service — vendors, purchase orders, goods receipts, three-way match.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.procurement import (
    GoodsReceipt,
    GoodsReceiptLine,
    InvoiceMatch,
    POStatus,
    PurchaseOrder,
    PurchaseOrderLine,
    Vendor,
    VendorStatus,
)
from app.services._base import DomainError, DomainService


_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9]{1}[A-Z]{1}[0-9A-Z]{1}$")


class ProcurementService(DomainService):
    domain = "procurement"

    # ---- Vendors -----------------------------------------------------------

    async def onboard_vendor(
        self,
        code: str,
        name: str,
        gstin: Optional[str] = None,
        pan: Optional[str] = None,
        payment_terms_days: int = 30,
        tds_applicable: bool = False,
        tds_rate: Decimal = Decimal("0.00"),
        **extra: Any,
    ) -> Vendor:
        if gstin and not _GSTIN_RE.match(gstin):
            raise DomainError(f"Invalid GSTIN format: {gstin}", "invalid_gstin")

        vendor = Vendor(
            org_id=self.org_id,
            code=code,
            name=name,
            gstin=gstin,
            pan=pan,
            payment_terms_days=payment_terms_days,
            tds_applicable=tds_applicable,
            tds_rate=tds_rate,
            status=VendorStatus.PENDING,
            **{k: v for k, v in extra.items() if hasattr(Vendor, k)},
        )
        self.db.add(vendor)
        await self.db.flush()
        return vendor

    async def approve_vendor(self, vendor_id: uuid.UUID, approved_by: uuid.UUID) -> Vendor:
        v = await self.db.get(Vendor, vendor_id)
        if v is None or v.org_id != self.org_id:
            raise DomainError("Vendor not found", "not_found")
        v.status = VendorStatus.APPROVED
        v.approved_by = approved_by
        await self.db.flush()
        return v

    # ---- Purchase Orders ---------------------------------------------------

    async def create_po(
        self,
        vendor_id: uuid.UUID,
        order_date: date,
        lines: list[dict[str, Any]],
        created_by: uuid.UUID,
        expected_delivery: Optional[date] = None,
        delivery_location: Optional[str] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        payment_terms: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PurchaseOrder:
        """
        Create a PO with lines.
        Each line: {description, quantity, rate, uom?, tax_rate?, hsn_code?, product_id?}
        """
        if not lines:
            raise DomainError("PO must have at least one line", "empty_po")

        vendor = await self.db.get(Vendor, vendor_id)
        if vendor is None or vendor.org_id != self.org_id:
            raise DomainError("Vendor not found", "vendor_not_found")
        if vendor.status == VendorStatus.BLACKLISTED:
            raise DomainError("Vendor is blacklisted", "blacklisted_vendor")

        subtotal = Decimal("0.00")
        tax_total = Decimal("0.00")
        prepared: list[dict[str, Any]] = []
        for i, line in enumerate(lines, start=1):
            qty = self._dec(line["quantity"])
            rate = self._dec(line["rate"])
            amount = (qty * rate).quantize(Decimal("0.01"))
            tax_rate = self._dec(line.get("tax_rate", 18))
            tax_amt = (amount * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
            subtotal += amount
            tax_total += tax_amt
            prepared.append({
                "line_number": i,
                "product_id": line.get("product_id"),
                "description": line["description"],
                "quantity": qty,
                "rate": rate,
                "amount": amount,
                "uom": line.get("uom", "NOS"),
                "tax_rate": tax_rate,
                "tax_amount": tax_amt,
                "hsn_code": line.get("hsn_code"),
            })

        po_number = await self._next_po_number()
        po = PurchaseOrder(
            org_id=self.org_id,
            po_number=po_number,
            vendor_id=vendor_id,
            order_date=order_date,
            expected_delivery=expected_delivery,
            delivery_location=delivery_location,
            warehouse_id=warehouse_id,
            subtotal=subtotal,
            tax_amount=tax_total,
            total_amount=subtotal + tax_total,
            currency="INR",
            status=POStatus.DRAFT,
            payment_terms=payment_terms,
            created_by=created_by,
            notes=notes,
        )
        self.db.add(po)
        await self.db.flush()

        for line in prepared:
            self.db.add(PurchaseOrderLine(po_id=po.id, **line))

        await self.db.flush()
        return po

    async def approve_po(self, po_id: uuid.UUID, approved_by: uuid.UUID) -> PurchaseOrder:
        po = await self.db.get(PurchaseOrder, po_id)
        if po is None or po.org_id != self.org_id:
            raise DomainError("PO not found", "not_found")
        if po.status != POStatus.DRAFT and po.status != POStatus.PENDING_APPROVAL:
            raise DomainError(f"PO cannot be approved in state {po.status.value}", "invalid_state")
        po.status = POStatus.APPROVED
        po.approved_by = approved_by
        await self.db.flush()
        return po

    async def _next_po_number(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"PO-{year}-"
        result = await self.db.execute(
            select(func.count(PurchaseOrder.id)).where(
                and_(
                    PurchaseOrder.org_id == self.org_id,
                    PurchaseOrder.po_number.like(f"{prefix}%"),
                )
            )
        )
        count = int(result.scalar() or 0) + 1
        return f"{prefix}{count:05d}"

    # ---- GRN ---------------------------------------------------------------

    async def record_grn(
        self,
        po_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        receipt_date: date,
        received_by: uuid.UUID,
        lines: list[dict[str, Any]],
        notes: Optional[str] = None,
    ) -> GoodsReceipt:
        """
        Line: {po_line_id, quantity_received, quantity_accepted, quantity_rejected?, batch_number?}
        """
        po = await self.db.get(PurchaseOrder, po_id)
        if po is None or po.org_id != self.org_id:
            raise DomainError("PO not found", "not_found")

        grn_number = await self._next_grn_number()
        grn = GoodsReceipt(
            org_id=self.org_id,
            grn_number=grn_number,
            po_id=po_id,
            vendor_id=po.vendor_id,
            warehouse_id=warehouse_id,
            receipt_date=receipt_date,
            received_by=received_by,
            status="received",
            notes=notes,
        )
        self.db.add(grn)
        await self.db.flush()

        total_lines = 0
        fully_received = True
        for line in lines:
            qty_recv = self._dec(line["quantity_received"])
            qty_accept = self._dec(line.get("quantity_accepted", qty_recv))
            qty_reject = self._dec(line.get("quantity_rejected", 0))

            po_line = await self.db.get(PurchaseOrderLine, line["po_line_id"])
            if po_line is None:
                raise DomainError("PO line not found", "not_found")
            po_line.received_quantity = (po_line.received_quantity or Decimal("0")) + qty_accept
            if po_line.received_quantity < po_line.quantity:
                fully_received = False

            self.db.add(GoodsReceiptLine(
                grn_id=grn.id,
                po_line_id=po_line.id,
                product_id=po_line.product_id,
                quantity_received=qty_recv,
                quantity_accepted=qty_accept,
                quantity_rejected=qty_reject,
                batch_number=line.get("batch_number"),
                rejection_reason=line.get("rejection_reason"),
            ))
            total_lines += 1

        po.status = POStatus.FULLY_RECEIVED if fully_received else POStatus.PARTIALLY_RECEIVED
        await self.db.flush()
        return grn

    async def _next_grn_number(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"GRN-{year}-"
        result = await self.db.execute(
            select(func.count(GoodsReceipt.id)).where(
                and_(
                    GoodsReceipt.org_id == self.org_id,
                    GoodsReceipt.grn_number.like(f"{prefix}%"),
                )
            )
        )
        count = int(result.scalar() or 0) + 1
        return f"{prefix}{count:05d}"

    # ---- Three-way match ---------------------------------------------------

    async def three_way_match(
        self,
        invoice_id: uuid.UUID,
        po_id: uuid.UUID,
        grn_id: Optional[uuid.UUID] = None,
        tolerance_pct: Decimal = Decimal("2.0"),
    ) -> InvoiceMatch:
        """Compare invoice vs PO vs GRN; record result."""
        from app.models.finance import Invoice

        inv = await self.db.get(Invoice, invoice_id)
        po = await self.db.get(PurchaseOrder, po_id)
        if inv is None or po is None:
            raise DomainError("Invoice or PO not found", "not_found")

        # Price match
        po_total = po.total_amount or Decimal("0")
        inv_total = inv.total_amount or Decimal("0")
        if po_total == 0:
            price_match = inv_total == 0
        else:
            diff_pct = abs(inv_total - po_total) / po_total * Decimal("100")
            price_match = diff_pct <= tolerance_pct

        # Quantity match (line by line, if GRN available)
        quantity_match = True
        if grn_id is not None:
            grn = await self.db.get(GoodsReceipt, grn_id)
            if grn is None:
                raise DomainError("GRN not found", "not_found")
            grn_lines = await self.db.execute(
                select(GoodsReceiptLine).where(GoodsReceiptLine.grn_id == grn_id)
            )
            accepted_by_po_line: dict[uuid.UUID, Decimal] = {}
            for gl in grn_lines.scalars():
                accepted_by_po_line.setdefault(gl.po_line_id, Decimal("0"))
                accepted_by_po_line[gl.po_line_id] += gl.quantity_accepted
            for po_line_id, qty in accepted_by_po_line.items():
                po_line = await self.db.get(PurchaseOrderLine, po_line_id)
                if po_line and qty < po_line.quantity:
                    quantity_match = False
                    break

        if price_match and quantity_match:
            status = "matched"
        elif not price_match:
            status = "price_mismatch"
        elif not quantity_match:
            status = "quantity_mismatch"
        else:
            status = "pending_grn"

        match = InvoiceMatch(
            org_id=self.org_id,
            invoice_id=invoice_id,
            po_id=po_id,
            grn_id=grn_id,
            match_status=status,
            quantity_match=quantity_match,
            price_match=price_match,
        )
        self.db.add(match)
        await self.db.flush()
        return match
