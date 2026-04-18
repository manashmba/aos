"""Fiscal calendar helpers (Indian FY: Apr–Mar)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


def fiscal_year_for(d: date) -> str:
    """Return Indian fiscal year label e.g. `FY2025-26` for 2025-06-01."""
    if d.month >= 4:
        return f"FY{d.year}-{(d.year + 1) % 100:02d}"
    return f"FY{d.year - 1}-{d.year % 100:02d}"


def fiscal_period_for(d: date) -> str:
    """Return 2-digit fiscal period (calendar month)."""
    return f"{d.month:02d}"


@dataclass(frozen=True)
class FiscalCalendar:
    """In-memory representation of which periods are locked.

    Keyed by (fiscal_year, fiscal_period). A locked period rejects new postings
    with `posting_period_locked`. A real implementation would persist this to
    a `fiscal_periods` table; for now we accept an explicit locked set.
    """
    locked_periods: frozenset[tuple[str, str]] = frozenset()
    current_period_start: Optional[date] = None

    def is_locked(self, d: date) -> bool:
        return (fiscal_year_for(d), fiscal_period_for(d)) in self.locked_periods

    def with_lock(self, fy: str, period: str) -> "FiscalCalendar":
        return FiscalCalendar(
            locked_periods=self.locked_periods | {(fy, period)},
            current_period_start=self.current_period_start,
        )
