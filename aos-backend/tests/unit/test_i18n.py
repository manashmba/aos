"""
Unit tests for app.core.i18n — language negotiation + LLM directive injection.

These are pure-function tests, no FastAPI app or DB needed.
"""

from __future__ import annotations

import pytest

from app.core.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGES,
    SUPPORTED_CODES,
    language,
    normalize,
    parse_accept_language,
    with_language_directive,
)


# ── parse_accept_language ──────────────────────────────────────────────────

@pytest.mark.parametrize(
    "header,expected",
    [
        ("hi-IN, en;q=0.5", "hi"),
        ("ta-IN", "ta"),
        ("en-US,en;q=0.9", "en"),
        # Unsupported tags fall through to next preference.
        ("ja, fr;q=0.9, ta;q=0.4", "ta"),
        # All unsupported → default.
        ("ja, ko, ru", "en"),
        # Quality factors are honoured (Hindi at 0.2 loses to Bengali at 0.9).
        ("hi;q=0.2, bn;q=0.9", "bn"),
        # Empty / missing.
        ("", "en"),
        (None, "en"),
        # Whitespace and trailing semis don't break parsing.
        ("  gu-IN  ;  q=0.8 , en ; q=0.1  ", "gu"),
    ],
)
def test_parse_accept_language(header, expected):
    assert parse_accept_language(header) == expected


def test_parse_accept_language_q_zero_excludes():
    """A `q=0` entry must be ignored even if it would otherwise match."""
    assert parse_accept_language("hi;q=0, en;q=0.1") == "en"


def test_parse_accept_language_custom_default():
    """Caller-supplied default applies when nothing matches."""
    assert parse_accept_language("ja", default="ta") == "ta"


# ── normalize / language ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "code,expected",
    [
        ("hi", "hi"),
        ("HI", "hi"),
        ("hi-IN", "hi"),
        ("hi_IN", "hi_in"),  # underscore not a valid BCP-47 separator → falls through
        (None, DEFAULT_LANGUAGE),
        ("", DEFAULT_LANGUAGE),
        ("ja", DEFAULT_LANGUAGE),
    ],
)
def test_normalize(code, expected):
    # underscore form is intentionally not split — it's malformed.
    if expected == "hi_in":
        assert normalize(code) == DEFAULT_LANGUAGE
    else:
        assert normalize(code) == expected


def test_language_returns_metadata():
    lang = language("hi-IN")
    assert lang.code == "hi"
    assert lang.native == "हिन्दी"
    assert lang.script_hint == "Devanagari"


def test_supported_codes_match_languages():
    """Catalogue and frozenset must stay in lockstep."""
    assert SUPPORTED_CODES == frozenset(l.code for l in LANGUAGES)
    assert "en" in SUPPORTED_CODES


# ── with_language_directive ────────────────────────────────────────────────

BASE_PROMPT = "You are the AOS finance agent."


def test_directive_noop_for_english():
    """English needs no extra directive — keep system prompt cache-stable."""
    assert with_language_directive(BASE_PROMPT, "en") == BASE_PROMPT
    assert with_language_directive(BASE_PROMPT, None) == BASE_PROMPT


@pytest.mark.parametrize("code,native", [
    ("hi", "हिन्दी"),
    ("ta", "தமிழ்"),
    ("bn", "বাংলা"),
    ("kn", "ಕನ್ನಡ"),
])
def test_directive_appends_native_label(code, native):
    out = with_language_directive(BASE_PROMPT, code)
    assert out.startswith(BASE_PROMPT)
    assert native in out
    # Reasoning we want the LLM to follow:
    assert "Latin digits" in out
    assert "lakh/crore" in out


def test_directive_handles_unknown_code():
    """Garbage code falls back to English — no exception, no directive."""
    assert with_language_directive(BASE_PROMPT, "xx-YY") == BASE_PROMPT
