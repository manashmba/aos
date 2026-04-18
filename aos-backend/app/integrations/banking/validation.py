"""Banking identifiers validation."""

from __future__ import annotations

import re


IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def is_valid_ifsc(ifsc: str) -> bool:
    return bool(ifsc) and bool(IFSC_RE.match(ifsc))


def is_valid_account_number(acct: str) -> bool:
    return bool(acct) and 9 <= len(acct) <= 18 and acct.isdigit()
