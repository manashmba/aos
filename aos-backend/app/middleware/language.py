"""
Language negotiation middleware.

Resolution order (highest priority first):
  1. `?lang=xx` query parameter — useful for share links and the WhatsApp bot
  2. `X-Language: xx` header — explicit override
  3. `Accept-Language` header — what every browser sends by default

The chosen code is stored in *both* `request.state.language` (so endpoints
can read it via `Depends(get_language)`) and the `current_language`
contextvar (so deeper layers — agents, services — can read it without
threading the parameter through their signatures).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_CODES,
    current_language,
    parse_accept_language,
)


class LanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        code = _resolve(request)
        token = current_language.set(code)
        request.state.language = code
        try:
            response = await call_next(request)
        finally:
            current_language.reset(token)
        # Echo the chosen code back so the client can confirm negotiation.
        response.headers["Content-Language"] = code
        return response


def _resolve(request: Request) -> str:
    # 1. ?lang=xx
    qp = request.query_params.get("lang")
    if qp:
        primary = qp.split("-", 1)[0].lower()
        if primary in SUPPORTED_CODES:
            return primary

    # 2. X-Language: xx
    explicit = request.headers.get("x-language")
    if explicit:
        primary = explicit.split("-", 1)[0].lower()
        if primary in SUPPORTED_CODES:
            return primary

    # 3. Accept-Language
    return parse_accept_language(request.headers.get("accept-language"), default=DEFAULT_LANGUAGE)
