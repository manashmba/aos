"""Bank adapter protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional, Protocol


@dataclass
class BankTransaction:
    transaction_id: str
    value_date: date
    amount: Decimal
    direction: str            # credit | debit
    description: str
    reference: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    balance: Optional[Decimal] = None


@dataclass
class PaymentInstruction:
    idempotency_key: str
    beneficiary_name: str
    beneficiary_account: str
    beneficiary_ifsc: str
    amount: Decimal
    mode: str                 # neft | rtgs | imps | upi
    remarks: Optional[str] = None
    value_date: Optional[date] = None


@dataclass
class PaymentResult:
    utr: str
    provider_reference: str
    status: str               # accepted | processing | completed | failed
    submitted_at: str
    raw: dict[str, Any] = field(default_factory=dict)


class BankProvider(Protocol):
    async def fetch_statement(self, account_number: str, from_date: date, to_date: date) -> list[BankTransaction]: ...
    async def initiate_payment(self, instruction: PaymentInstruction) -> PaymentResult: ...
    async def payment_status(self, utr: str) -> dict[str, Any]: ...
    async def current_balance(self, account_number: str) -> Decimal: ...
