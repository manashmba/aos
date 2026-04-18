"""OCR adapter protocol — invoice/receipt/GSTIN extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional, Protocol


@dataclass
class OCRResult:
    confidence: float              # 0..1
    raw_text: str = ""
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    line_items: list[dict[str, Any]] = field(default_factory=list)
    extracted_fields: dict[str, Any] = field(default_factory=dict)


class OCRProvider(Protocol):
    async def extract_invoice(self, file_url_or_bytes: Any) -> OCRResult: ...
    async def extract_receipt(self, file_url_or_bytes: Any) -> OCRResult: ...
