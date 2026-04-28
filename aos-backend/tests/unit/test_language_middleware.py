"""
Middleware test: LanguageMiddleware resolves the per-request language and
exposes it on `request.state.language`, the `current_language` contextvar,
and a `Content-Language` response header.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.i18n import current_language
from app.middleware.language import LanguageMiddleware


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(LanguageMiddleware)

    @app.get("/echo")
    async def echo(request: Request):
        return {
            "from_state": getattr(request.state, "language", None),
            "from_contextvar": current_language.get(),
        }

    return app


def test_middleware_defaults_to_en_when_no_header():
    client = TestClient(_app())
    res = client.get("/echo")
    assert res.status_code == 200
    body = res.json()
    assert body["from_state"] == "en"
    assert body["from_contextvar"] == "en"
    assert res.headers["content-language"] == "en"


def test_middleware_reads_accept_language():
    client = TestClient(_app())
    res = client.get("/echo", headers={"Accept-Language": "hi-IN, en;q=0.5"})
    assert res.json() == {"from_state": "hi", "from_contextvar": "hi"}
    assert res.headers["content-language"] == "hi"


def test_middleware_x_language_overrides_accept_language():
    client = TestClient(_app())
    res = client.get(
        "/echo",
        headers={"Accept-Language": "ta-IN", "X-Language": "bn"},
    )
    assert res.json()["from_state"] == "bn"


def test_middleware_query_param_wins_over_headers():
    client = TestClient(_app())
    res = client.get(
        "/echo?lang=gu",
        headers={"Accept-Language": "hi-IN", "X-Language": "ta"},
    )
    assert res.json()["from_state"] == "gu"


def test_middleware_unknown_lang_falls_back_to_en():
    client = TestClient(_app())
    res = client.get("/echo?lang=xx", headers={"Accept-Language": "ja"})
    assert res.json()["from_state"] == "en"
    assert res.headers["content-language"] == "en"


def test_middleware_resets_contextvar_after_request():
    """Two back-to-back requests must not leak the previous language."""
    client = TestClient(_app())
    client.get("/echo", headers={"Accept-Language": "kn"})
    res = client.get("/echo")
    assert res.json()["from_contextvar"] == "en"
