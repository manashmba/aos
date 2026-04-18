"""
Posting rules — declarative mapping of business events to debit/credit
account codes. The LedgerEngine resolves account codes to account ids per org.

Each rule takes a context dict and returns a list of lines:
    {"account_code": str, "debit": Decimal|None, "credit": Decimal|None,
     "description": str?, "cost_center": str?, "entity_type": str?, "entity_id": UUID?}
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable


@dataclass(frozen=True)
class PostingRule:
    event: str
    description: str
    build_lines: Callable[[dict[str, Any]], list[dict[str, Any]]]


def _d(v: Any) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


# ---- Sales invoice (customer invoice) --------------------------------------

def _sales_invoice(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    subtotal = _d(ctx["subtotal"])
    tax = _d(ctx.get("tax_amount", 0))
    total = subtotal + tax
    lines = [
        {
            "account_code": "1200",  # Accounts Receivable
            "debit": total,
            "description": f"AR — invoice {ctx.get('invoice_number')}",
            "entity_type": "customer",
            "entity_id": ctx.get("customer_id"),
        },
        {
            "account_code": "4000",  # Sales Revenue
            "credit": subtotal,
            "description": "Sales revenue",
        },
    ]
    if tax > 0:
        lines.append({
            "account_code": "2300",  # Output GST Payable
            "credit": tax,
            "description": "Output GST",
        })
    return lines


# ---- Purchase invoice (vendor bill) ----------------------------------------

def _purchase_invoice(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    subtotal = _d(ctx["subtotal"])
    tax = _d(ctx.get("tax_amount", 0))
    total = subtotal + tax
    expense_code = ctx.get("expense_account_code", "5000")  # default Purchases
    lines = [
        {
            "account_code": expense_code,
            "debit": subtotal,
            "description": f"Purchase — bill {ctx.get('invoice_number')}",
        },
    ]
    if tax > 0:
        lines.append({
            "account_code": "1300",  # Input GST Receivable
            "debit": tax,
            "description": "Input GST",
        })
    lines.append({
        "account_code": "2100",  # Accounts Payable
        "credit": total,
        "description": f"AP — bill {ctx.get('invoice_number')}",
        "entity_type": "vendor",
        "entity_id": ctx.get("vendor_id"),
    })
    return lines


# ---- Customer payment received ---------------------------------------------

def _payment_received(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    amount = _d(ctx["amount"])
    tds = _d(ctx.get("tds_amount", 0))
    cash_code = ctx.get("cash_account_code", "1100")  # Bank
    lines = [
        {"account_code": cash_code, "debit": amount - tds, "description": "Bank receipt"},
    ]
    if tds > 0:
        lines.append({
            "account_code": "1310",  # TDS Receivable
            "debit": tds,
            "description": f"TDS u/s {ctx.get('tds_section', '')}",
        })
    lines.append({
        "account_code": "1200",  # AR
        "credit": amount,
        "description": f"Payment against invoice {ctx.get('invoice_number', '')}",
        "entity_type": "customer",
        "entity_id": ctx.get("customer_id"),
    })
    return lines


# ---- Vendor payment made ---------------------------------------------------

def _payment_made(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    amount = _d(ctx["amount"])
    tds = _d(ctx.get("tds_amount", 0))
    cash_code = ctx.get("cash_account_code", "1100")
    lines = [
        {
            "account_code": "2100",  # AP
            "debit": amount,
            "description": f"Payment against bill {ctx.get('invoice_number', '')}",
            "entity_type": "vendor",
            "entity_id": ctx.get("vendor_id"),
        },
    ]
    if tds > 0:
        lines.append({
            "account_code": "2310",  # TDS Payable
            "credit": tds,
            "description": f"TDS u/s {ctx.get('tds_section', '')}",
        })
    lines.append({"account_code": cash_code, "credit": amount - tds, "description": "Bank payment"})
    return lines


# ---- Inventory receipt (GRN) -----------------------------------------------

def _inventory_receipt(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    value = _d(ctx["value"])
    return [
        {"account_code": "1400", "debit": value, "description": "Inventory on hand"},  # Inventory
        {"account_code": "2110", "credit": value, "description": "GRNI — goods received not invoiced"},
    ]


# ---- Inventory issue (to production / consumption) -------------------------

def _inventory_issue(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    value = _d(ctx["value"])
    return [
        {"account_code": ctx.get("expense_account_code", "5100"), "debit": value, "description": "COGS / material consumed"},
        {"account_code": "1400", "credit": value, "description": "Inventory on hand"},
    ]


# ---- Payroll posting -------------------------------------------------------

def _payroll(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    gross = _d(ctx["gross"])
    pf = _d(ctx.get("pf", 0))
    esi = _d(ctx.get("esi", 0))
    tds = _d(ctx.get("tds", 0))
    net = gross - pf - esi - tds
    return [
        {"account_code": "5500", "debit": gross, "description": "Salaries & wages"},
        {"account_code": "2400", "credit": pf, "description": "PF payable"},
        {"account_code": "2410", "credit": esi, "description": "ESI payable"},
        {"account_code": "2310", "credit": tds, "description": "TDS payable"},
        {"account_code": "2500", "credit": net, "description": "Salaries payable"},
    ]


POSTING_RULES: dict[str, PostingRule] = {
    "sales.invoice_posted": PostingRule(
        "sales.invoice_posted", "Customer invoice", _sales_invoice,
    ),
    "procurement.bill_posted": PostingRule(
        "procurement.bill_posted", "Vendor bill", _purchase_invoice,
    ),
    "finance.payment_received": PostingRule(
        "finance.payment_received", "Customer payment", _payment_received,
    ),
    "finance.payment_made": PostingRule(
        "finance.payment_made", "Vendor payment", _payment_made,
    ),
    "inventory.goods_received": PostingRule(
        "inventory.goods_received", "Inventory receipt", _inventory_receipt,
    ),
    "inventory.goods_issued": PostingRule(
        "inventory.goods_issued", "Inventory issue", _inventory_issue,
    ),
    "hr.payroll_run": PostingRule(
        "hr.payroll_run", "Payroll accrual", _payroll,
    ),
}
