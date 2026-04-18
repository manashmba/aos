"""GST provider protocol — e-invoice (IRN), e-waybill, GSTR filing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional, Protocol


@dataclass
class EInvoiceRequest:
    invoice_number: str
    invoice_date: date
    supplier_gstin: str
    buyer_gstin: Optional[str]
    buyer_name: str
    buyer_state_code: Optional[str]
    line_items: list[dict[str, Any]]
    subtotal: Decimal
    cgst: Decimal = Decimal("0.00")
    sgst: Decimal = Decimal("0.00")
    igst: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
    po_reference: Optional[str] = None


@dataclass
class EInvoiceResponse:
    irn: str                  # 64-char Invoice Reference Number
    ack_number: str
    ack_date: str
    signed_qr_code: str
    signed_invoice: str
    status: str = "active"
    provider_raw: dict[str, Any] = field(default_factory=dict)


class GSTProvider(Protocol):
    async def generate_irn(self, req: EInvoiceRequest) -> EInvoiceResponse: ...
    async def cancel_irn(self, irn: str, reason: str) -> dict[str, Any]: ...
    async def generate_ewaybill(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def file_gstr1(self, period: str, payload: dict[str, Any]) -> dict[str, Any]: ...
