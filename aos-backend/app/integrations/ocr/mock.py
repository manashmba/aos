"""Mock OCR provider — returns a canned high-confidence extraction."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.integrations.ocr.protocol import OCRResult


class MockOCRProvider:
    def __init__(self, canned: OCRResult | None = None):
        self.canned = canned

    async def extract_invoice(self, file_url_or_bytes: Any) -> OCRResult:
        if self.canned is not None:
            return self.canned
        return OCRResult(
            confidence=0.92,
            raw_text="Mock invoice text",
            vendor_name="Acme Supplies Pvt Ltd",
            vendor_gstin="27AAAPL1234C1Z5",
            invoice_number="ACM-2024-0001",
            invoice_date="2024-11-01",
            subtotal=Decimal("10000.00"),
            tax_amount=Decimal("1800.00"),
            total_amount=Decimal("11800.00"),
            line_items=[{
                "description": "Office supplies",
                "quantity": Decimal("10"),
                "rate": Decimal("1000.00"),
                "hsn_code": "4820",
            }],
            extracted_fields={"place_of_supply": "Maharashtra"},
        )

    async def extract_receipt(self, file_url_or_bytes: Any) -> OCRResult:
        return OCRResult(
            confidence=0.85,
            raw_text="Mock receipt",
            vendor_name="Local Kirana",
            total_amount=Decimal("450.00"),
        )
