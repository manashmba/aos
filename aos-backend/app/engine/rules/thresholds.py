"""
AOS Business Thresholds — simple KV store for org-level numeric limits.

Examples:
  - finance.min_cash_balance        = 500000
  - procurement.po_auto_approve_max = 25000
  - sales.credit_check_threshold    = 100000
  - hr.leave.max_consecutive_days   = 15

These are cached in-process and can be refreshed at runtime.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional


DEFAULT_THRESHOLDS: dict[str, Any] = {
    # Finance
    "finance.min_cash_balance": Decimal("500000"),
    "finance.payment_auto_approve_max": Decimal("50000"),
    "finance.gst_reconciliation_tolerance": Decimal("1.00"),

    # Procurement
    "procurement.po_auto_approve_max": Decimal("25000"),
    "procurement.three_way_match_tolerance_pct": Decimal("2.0"),
    "procurement.vendor_credit_days_max": 90,

    # Sales
    "sales.credit_check_threshold": Decimal("100000"),
    "sales.discount_auto_approve_pct": Decimal("5.0"),
    "sales.order_min_margin_pct": Decimal("10.0"),

    # Inventory
    "inventory.reorder_lead_time_days": 14,
    "inventory.cycle_count_frequency_days": 30,

    # HR
    "hr.leave.max_consecutive_days": 15,
    "hr.reimbursement_auto_approve_max": Decimal("5000"),

    # Agent / AI
    "agent.max_tool_calls_per_turn": 10,
    "agent.min_confidence_to_execute": Decimal("0.80"),
    "agent.max_tokens_per_session": 500000,
}


class Thresholds:
    """In-process threshold cache with override support."""

    def __init__(self, overrides: Optional[dict[str, Any]] = None) -> None:
        self._store: dict[str, Any] = dict(DEFAULT_THRESHOLDS)
        if overrides:
            self._store.update(overrides)

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def get_decimal(self, key: str, default: Decimal = Decimal("0")) -> Decimal:
        val = self._store.get(key, default)
        if isinstance(val, Decimal):
            return val
        return Decimal(str(val))

    def get_int(self, key: str, default: int = 0) -> int:
        val = self._store.get(key, default)
        return int(val)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def update(self, values: dict[str, Any]) -> None:
        self._store.update(values)

    def all(self) -> dict[str, Any]:
        return dict(self._store)
