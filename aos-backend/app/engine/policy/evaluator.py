"""
AOS Rule Evaluator — evaluates `when` conditions against an action context.

Supported operators:
  eq, ne, gt, gte, lt, lte, in, not_in, contains, starts_with, exists, regex

Context is a flat dict that may contain nested dicts; dotted paths are
supported in `field` (e.g., "vendor.gstin").
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.engine.policy.rules import Rule, to_decimal


def _resolve_path(context: dict[str, Any], path: str) -> Any:
    """Walk a dotted path through nested dicts."""
    cur: Any = context
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _compare_numeric(lhs: Any, rhs: Any, op: str) -> bool:
    try:
        l = to_decimal(lhs)
        r = to_decimal(rhs)
    except (InvalidOperation, TypeError, ValueError):
        return False
    if op == "gt":
        return l > r
    if op == "gte":
        return l >= r
    if op == "lt":
        return l < r
    if op == "lte":
        return l <= r
    return False


def evaluate_condition(cond: dict[str, Any], context: dict[str, Any]) -> bool:
    """Evaluate a single condition dict against context."""
    field = cond.get("field")
    op = cond.get("op", "eq")
    expected = cond.get("value")

    if field is None:
        return False

    actual = _resolve_path(context, field)

    if op == "exists":
        return actual is not None
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op in ("gt", "gte", "lt", "lte"):
        return _compare_numeric(actual, expected, op)
    if op == "in":
        return actual in (expected or [])
    if op == "not_in":
        return actual not in (expected or [])
    if op == "contains":
        if actual is None:
            return False
        return expected in actual
    if op == "starts_with":
        return isinstance(actual, str) and actual.startswith(str(expected))
    if op == "regex":
        return isinstance(actual, str) and re.search(str(expected), actual) is not None

    return False


def rule_matches(rule: Rule, context: dict[str, Any]) -> bool:
    """A rule matches if ALL its `when` conditions evaluate true."""
    if not rule.when:
        return True  # rule with no conditions always fires
    return all(evaluate_condition(c, context) for c in rule.when)
