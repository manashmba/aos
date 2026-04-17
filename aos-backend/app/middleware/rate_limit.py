"""
AOS Rate Limiting Middleware
Token-bucket rate limiting via Redis.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.logging import get_logger
from app.core.redis import redis_client

logger = get_logger("rate_limit")

# Requests per minute per user/IP
DEFAULT_RATE_LIMIT = 120
LLM_RATE_LIMIT = 30  # Stricter for AI endpoints


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        client_key = self._get_client_key(request)
        is_llm_path = "/conversation" in request.url.path or "/agents" in request.url.path
        limit = LLM_RATE_LIMIT if is_llm_path else DEFAULT_RATE_LIMIT

        allowed = await self._check_rate_limit(client_key, limit)
        if not allowed:
            logger.warning("rate_limit_exceeded", client_key=client_key)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again shortly."},
            )

        return await call_next(request)

    def _get_client_key(self, request: Request) -> str:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                payload = decode_token(auth_header[7:])
                return f"rl:user:{payload.get('sub', 'unknown')}"
            except Exception:
                pass
        client_ip = request.client.host if request.client else "unknown"
        return f"rl:ip:{client_ip}"

    async def _check_rate_limit(self, key: str, limit: int) -> bool:
        try:
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, 60)
            return current <= limit
        except Exception:
            # If Redis is down, allow the request
            return True
