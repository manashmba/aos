"""GSTIN format validation + state code helpers."""

from __future__ import annotations

import re
from typing import Optional


# 2 state + 10 PAN + 1 entity + 1 Z + 1 check
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$")


def is_valid_gstin(gstin: str) -> bool:
    if not gstin or len(gstin) != 15:
        return False
    return bool(GSTIN_RE.match(gstin))


def state_code_from_gstin(gstin: str) -> Optional[str]:
    if not is_valid_gstin(gstin):
        return None
    return gstin[:2]


def is_intra_state(supplier_gstin: str, buyer_gstin: Optional[str], buyer_state_code: Optional[str] = None) -> bool:
    """True if supplier + buyer are in the same state (CGST+SGST applies)."""
    supplier_state = state_code_from_gstin(supplier_gstin)
    if not supplier_state:
        return False
    buyer_state = state_code_from_gstin(buyer_gstin) if buyer_gstin else buyer_state_code
    if not buyer_state:
        return False
    return supplier_state == buyer_state
