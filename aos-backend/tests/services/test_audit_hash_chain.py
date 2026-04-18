"""Unit tests for the audit hash-chain compute function (pure, no DB)."""

from __future__ import annotations

from app.services.audit.service import compute_hash


def test_hash_deterministic():
    p = {"event_type": "x", "amount": "100"}
    h1 = compute_hash(None, p)
    h2 = compute_hash(None, p)
    assert h1 == h2
    assert len(h1) == 64


def test_chain_changes_with_previous():
    p = {"event_type": "x"}
    h_root = compute_hash(None, p)
    h_next = compute_hash(h_root, p)
    assert h_next != h_root


def test_tamper_detected():
    p1 = {"event_type": "invoice.posted", "amount": "1000"}
    h1 = compute_hash(None, p1)
    # same payload re-hashed with a different previous -> different hash
    h_tamper = compute_hash("deadbeef", p1)
    assert h_tamper != h1


def test_payload_key_order_irrelevant():
    assert compute_hash(None, {"a": 1, "b": 2}) == compute_hash(None, {"b": 2, "a": 1})
