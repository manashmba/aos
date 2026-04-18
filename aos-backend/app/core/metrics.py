"""
Prometheus metrics registry.

Soft-imports prometheus_client so the app still runs if it isn't installed.
Metric helpers are no-ops in that case.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any

try:
    from prometheus_client import (  # type: ignore
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    _PROM = True
except ImportError:  # pragma: no cover
    _PROM = False
    CONTENT_TYPE_LATEST = "text/plain"

    class _NoOp:
        def __init__(self, *a, **kw): ...
        def labels(self, **kw): return self
        def inc(self, n: float = 1.0): ...
        def dec(self, n: float = 1.0): ...
        def set(self, v: float): ...
        def observe(self, v: float): ...

    Counter = Histogram = Gauge = _NoOp  # type: ignore

    class CollectorRegistry:  # type: ignore
        pass

    def generate_latest(*a, **kw) -> bytes:  # type: ignore
        return b"# prometheus_client not installed\n"


REGISTRY = CollectorRegistry() if _PROM else None


def _counter(name: str, desc: str, labels: list[str] | None = None) -> Counter:
    if _PROM:
        return Counter(name, desc, labelnames=labels or [], registry=REGISTRY)
    return Counter()


def _histogram(name: str, desc: str, labels: list[str] | None = None, buckets=None) -> Histogram:
    if _PROM:
        kwargs: dict[str, Any] = {"labelnames": labels or [], "registry": REGISTRY}
        if buckets:
            kwargs["buckets"] = buckets
        return Histogram(name, desc, **kwargs)
    return Histogram()


def _gauge(name: str, desc: str, labels: list[str] | None = None) -> Gauge:
    if _PROM:
        return Gauge(name, desc, labelnames=labels or [], registry=REGISTRY)
    return Gauge()


# ---- Metrics ---------------------------------------------------------------

http_requests_total = _counter(
    "aos_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
http_request_duration_seconds = _histogram(
    "aos_http_request_duration_seconds", "HTTP request duration",
    labels=["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

agent_tool_calls_total = _counter(
    "aos_agent_tool_calls_total", "Agent tool calls", ["agent", "tool", "outcome"]
)
agent_tool_call_duration_seconds = _histogram(
    "aos_agent_tool_call_duration_seconds", "Tool call duration",
    labels=["agent", "tool"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)

llm_tokens_total = _counter(
    "aos_llm_tokens_total", "LLM tokens consumed", ["model", "direction"]
)
llm_requests_total = _counter(
    "aos_llm_requests_total", "LLM requests", ["model", "outcome"]
)
llm_request_duration_seconds = _histogram(
    "aos_llm_request_duration_seconds", "LLM request duration", labels=["model"],
    buckets=(0.25, 0.5, 1, 2, 5, 10, 20, 30, 60),
)

policy_blocks_total = _counter(
    "aos_policy_blocks_total", "Policy engine blocks", ["domain", "action", "rule"]
)
approvals_triggered_total = _counter(
    "aos_approvals_triggered_total", "Approvals triggered", ["domain", "action"]
)

ledger_postings_total = _counter(
    "aos_ledger_postings_total", "Ledger journal entries posted", ["event", "outcome"]
)

conversation_turns_total = _counter(
    "aos_conversation_turns_total", "Conversation turns", ["agent", "outcome"]
)

active_sessions = _gauge(
    "aos_active_sessions", "Currently active conversation sessions"
)


@contextmanager
def time_block(histogram, **labels):
    start = time.monotonic()
    try:
        yield
    finally:
        dur = time.monotonic() - start
        if labels:
            histogram.labels(**labels).observe(dur)
        else:
            histogram.observe(dur)


def metrics_response() -> tuple[bytes, str]:
    """Return (body, content_type) for /metrics."""
    if REGISTRY is not None:
        return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST  # type: ignore[arg-type]
