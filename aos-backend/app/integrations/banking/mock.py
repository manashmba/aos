"""Mock bank provider — simulated balance, deterministic UTRs."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from app.integrations.banking.protocol import (
    BankTransaction,
    PaymentInstruction,
    PaymentResult,
)


class MockBankProvider:
    def __init__(self, starting_balance: Decimal = Decimal("10000000.00")):
        self._balance = starting_balance
        self.payments: dict[str, PaymentResult] = {}
        self.seen_idempotency: dict[str, str] = {}
        self.statements: list[BankTransaction] = []

    async def fetch_statement(self, account_number: str, from_date: date, to_date: date) -> list[BankTransaction]:
        return [t for t in self.statements if from_date <= t.value_date <= to_date]

    async def initiate_payment(self, instruction: PaymentInstruction) -> PaymentResult:
        if instruction.idempotency_key in self.seen_idempotency:
            utr = self.seen_idempotency[instruction.idempotency_key]
            return self.payments[utr]

        if instruction.amount <= 0:
            raise ValueError("payment amount must be positive")
        if instruction.amount > self._balance:
            result = PaymentResult(
                utr=f"UTR{uuid.uuid4().hex[:10].upper()}",
                provider_reference=f"REF{uuid.uuid4().hex[:8].upper()}",
                status="failed",
                submitted_at=datetime.now(timezone.utc).isoformat(),
                raw={"reason": "insufficient_balance"},
            )
            self.payments[result.utr] = result
            self.seen_idempotency[instruction.idempotency_key] = result.utr
            return result

        utr = f"UTR{uuid.uuid4().hex[:10].upper()}"
        result = PaymentResult(
            utr=utr,
            provider_reference=f"REF{uuid.uuid4().hex[:8].upper()}",
            status="accepted",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            raw={"mode": instruction.mode},
        )
        self._balance -= instruction.amount
        self.payments[utr] = result
        self.seen_idempotency[instruction.idempotency_key] = utr
        self.statements.append(BankTransaction(
            transaction_id=utr,
            value_date=instruction.value_date or date.today(),
            amount=instruction.amount,
            direction="debit",
            description=f"{instruction.mode.upper()} to {instruction.beneficiary_name}",
            reference=instruction.remarks,
            counterparty_name=instruction.beneficiary_name,
            counterparty_account=instruction.beneficiary_account,
            balance=self._balance,
        ))
        return result

    async def payment_status(self, utr: str) -> dict[str, Any]:
        r = self.payments.get(utr)
        if r is None:
            return {"utr": utr, "status": "unknown"}
        return {"utr": utr, "status": r.status, "raw": r.raw}

    async def current_balance(self, account_number: str) -> Decimal:
        return self._balance
