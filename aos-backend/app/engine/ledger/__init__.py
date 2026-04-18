"""
Ledger Engine — deterministic double-entry posting.

Turns domain events (invoice posted, payment received, stock issued, payroll run)
into balanced journal entries via configurable posting rules.
"""
from app.engine.ledger.engine import LedgerEngine, PostingError
from app.engine.ledger.fiscal import FiscalCalendar, fiscal_year_for
from app.engine.ledger.posting_rules import PostingRule, POSTING_RULES

__all__ = [
    "LedgerEngine",
    "PostingError",
    "FiscalCalendar",
    "fiscal_year_for",
    "PostingRule",
    "POSTING_RULES",
]
