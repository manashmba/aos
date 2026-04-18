"""
Observability middleware — correlation id + request metrics.

Bounds a `correlation_id` and `request_id` into structlog context vars so
every log line for a request carries them; emits Prometheus request counters
and latency histograms.
"""

from __future__ import annotations

import time
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import (
    http_request_duration_seconds,
    http_requests_total,
)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("x-correlation-id") or str(uuid4())
        request_id = str(uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
        )

        request.state.correlation_id = correlation_id
        start = time.monotonic()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.monotonic() - start
            path_label = request.url.path
            http_requests_total.labels(
                method=request.method, path=path_label, status=str(status_code)
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method, path=path_label
            ).observe(duration)
