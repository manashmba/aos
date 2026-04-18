"""Unit tests for ledger posting rules — pure functions, no DB required."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.engine.ledger.fiscal import FiscalCalendar, fiscal_period_for, fiscal_year_for
from app.engine.ledger.posting_rules import POSTING_RULES


def _sum(lines, key):
    return sum((Decimal(str(l.get(key) or 0)) for l in lines), Decimal("0"))


def test_fiscal_year_indian():
    from datetime import date
    assert fiscal_year_for(date(2025, 4, 1)) == "FY2025-26"
    assert fiscal_year_for(date(2025, 3, 31)) == "FY2024-25"
    assert fiscal_period_for(date(2025, 6, 15)) == "06"


def test_fiscal_lock():
    from datetime import date
    cal = FiscalCalendar().with_lock("FY2024-25", "03")
    assert cal.is_locked(date(2025, 3, 10)) is True
    assert cal.is_locked(date(2025, 4, 1)) is False


def test_sales_invoice_balanced():
    rule = POSTING_RULES["sales.invoice_posted"]
    lines = rule.build_lines({
        "subtotal": Decimal("1000"),
        "tax_amount": Decimal("180"),
        "invoice_number": "INV-1",
        "customer_id": "c1",
    })
    assert _sum(lines, "debit") == _sum(lines, "credit")
    codes = [l["account_code"] for l in lines]
    assert "1200" in codes  # AR
    assert "4000" in codes  # Sales
    assert "2300" in codes  # Output GST


def test_sales_invoice_no_tax():
    rule = POSTING_RULES["sales.invoice_posted"]
    lines = rule.build_lines({
        "subtotal": Decimal("500"),
        "tax_amount": Decimal("0"),
    })
    assert _sum(lines, "debit") == _sum(lines, "credit")
    assert len(lines) == 2  # No GST line


def test_purchase_invoice_balanced():
    rule = POSTING_RULES["procurement.bill_posted"]
    lines = rule.build_lines({
        "subtotal": Decimal("10000"),
        "tax_amount": Decimal("1800"),
        "invoice_number": "BILL-1",
        "vendor_id": "v1",
    })
    assert _sum(lines, "debit") == _sum(lines, "credit") == Decimal("11800")


def test_payment_received_with_tds():
    rule = POSTING_RULES["finance.payment_received"]
    lines = rule.build_lines({
        "amount": Decimal("100000"),
        "tds_amount": Decimal("10000"),
        "tds_section": "194C",
        "invoice_number": "INV-7",
        "customer_id": "c1",
    })
    assert _sum(lines, "debit") == _sum(lines, "credit") == Decimal("100000")
    # Bank gets net, TDS receivable gets withheld portion
    bank = next(l for l in lines if l["account_code"] == "1100")
    tds = next(l for l in lines if l["account_code"] == "1310")
    assert bank["debit"] == Decimal("90000")
    assert tds["debit"] == Decimal("10000")


def test_payroll_balanced():
    rule = POSTING_RULES["hr.payroll_run"]
    lines = rule.build_lines({
        "gross": Decimal("100000"),
        "pf": Decimal("12000"),
        "esi": Decimal("750"),
        "tds": Decimal("8000"),
    })
    assert _sum(lines, "debit") == _sum(lines, "credit") == Decimal("100000")


def test_inventory_receipt_balanced():
    rule = POSTING_RULES["inventory.goods_received"]
    lines = rule.build_lines({"value": Decimal("50000")})
    assert _sum(lines, "debit") == _sum(lines, "credit") == Decimal("50000")


def test_inventory_issue_balanced():
    rule = POSTING_RULES["inventory.goods_issued"]
    lines = rule.build_lines({"value": Decimal("25000"), "expense_account_code": "5100"})
    assert _sum(lines, "debit") == _sum(lines, "credit") == Decimal("25000")
