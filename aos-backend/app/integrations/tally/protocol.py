"""Tally adapter — XML-based voucher sync."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional, Protocol


@dataclass
class TallyLedger:
    name: str
    parent_group: str
    opening_balance: Decimal = Decimal("0.00")


@dataclass
class TallyVoucher:
    voucher_type: str              # Sales | Purchase | Payment | Receipt | Journal
    voucher_number: str
    voucher_date: date
    narration: Optional[str] = None
    entries: list[dict[str, Any]] = field(default_factory=list)  # [{ledger, debit|credit, amount}]


class TallyProvider(Protocol):
    async def push_voucher(self, voucher: TallyVoucher) -> dict[str, Any]: ...
    async def push_ledger(self, ledger: TallyLedger) -> dict[str, Any]: ...
    async def fetch_vouchers(self, from_date: date, to_date: date) -> list[TallyVoucher]: ...
    async def export_xml(self, vouchers: list[TallyVoucher]) -> str: ...
