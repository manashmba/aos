"""Mock GST provider — deterministic IRN + QR, for tests and local dev."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from app.integrations.gst.protocol import EInvoiceRequest, EInvoiceResponse


class MockGSTProvider:
    def __init__(self) -> None:
        self.irns: dict[str, dict[str, Any]] = {}

    async def generate_irn(self, req: EInvoiceRequest) -> EInvoiceResponse:
        payload = f"{req.supplier_gstin}|{req.invoice_number}|{req.invoice_date.isoformat()}|{req.total}"
        irn = hashlib.sha256(payload.encode()).hexdigest()
        ack = f"ACK{uuid.uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        qr = f"MOCKQR::{irn[:16]}::{req.total}"
        resp = EInvoiceResponse(
            irn=irn,
            ack_number=ack,
            ack_date=now,
            signed_qr_code=qr,
            signed_invoice=f"SIGNED::{irn}",
            status="active",
            provider_raw={"note": "mock-irn"},
        )
        self.irns[irn] = {"request": req, "response": resp}
        return resp

    async def cancel_irn(self, irn: str, reason: str) -> dict[str, Any]:
        if irn not in self.irns:
            return {"status": "not_found"}
        self.irns[irn]["response"].status = "cancelled"
        self.irns[irn]["cancel_reason"] = reason
        return {"irn": irn, "status": "cancelled"}

    async def generate_ewaybill(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "ewb_number": f"EWB{uuid.uuid4().hex[:10].upper()}",
            "valid_until": "mock-24h",
            "status": "active",
        }

    async def file_gstr1(self, period: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "period": period,
            "reference_id": f"GSTR1-{uuid.uuid4().hex[:8]}",
            "status": "accepted",
        }
