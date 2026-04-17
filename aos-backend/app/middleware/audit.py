"""
AOS Audit Middleware
Logs every API request with context for full audit trail.
"""

import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger("audit")


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every request with timing and context."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id

        start_time = time.monotonic()

        # Extract user info from token if present
        user_id = "anonymous"
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                payload = decode_token(auth_header[7:])
                user_id = payload.get("sub", "unknown")
            except Exception:
                user_id = "invalid_token"

        response = await call_next(request)

        duration_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "api_request",
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            user_id=user_id,
            client_ip=request.client.host if request.client else "unknown",
        )

        response.headers["X-Request-ID"] = request_id
        return response
