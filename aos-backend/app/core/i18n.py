"""
AOS Backend i18n — language negotiation and LLM prompt localisation.

Mirrors the 8 frontend languages so the agent can respond in the user's
language. Two layers:

  1. *Negotiation* — `parse_accept_language()` interprets the standard HTTP
     `Accept-Language` header and picks the best supported match. Used by
     `LanguageMiddleware` to set a per-request contextvar.

  2. *LLM directive* — `with_language_directive(system_prompt, lang)` appends
     a short "respond in <native>" instruction to the system prompt before
     it is shipped to Claude / OpenAI.

We intentionally do NOT translate API error messages here; localised UX
strings live on the frontend. The agent's *generated* response is the only
place where the backend speaks to the user, so that's the only place we
need to localise on this side.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Language:
    code: str           # ISO-639-1 (en, hi, ta, …)
    native: str         # Native script label (हिन्दी, தமிழ், …)
    english: str        # English name (Hindi, Tamil, …)
    bcp47: str          # Full BCP-47 (en-IN, hi-IN, …) for Intl-style use
    script_hint: str    # Free-form script note for the LLM


# Keep this list in sync with aos-frontend/src/i18n/index.ts
LANGUAGES: tuple[Language, ...] = (
    Language("en", "English",   "English",   "en-IN", "Latin"),
    Language("hi", "हिन्दी",     "Hindi",     "hi-IN", "Devanagari"),
    Language("bn", "বাংলা",     "Bengali",   "bn-IN", "Bengali"),
    Language("ta", "தமிழ்",     "Tamil",     "ta-IN", "Tamil"),
    Language("te", "తెలుగు",    "Telugu",    "te-IN", "Telugu"),
    Language("mr", "मराठी",      "Marathi",   "mr-IN", "Devanagari"),
    Language("gu", "ગુજરાતી",   "Gujarati",  "gu-IN", "Gujarati"),
    Language("kn", "ಕನ್ನಡ",      "Kannada",   "kn-IN", "Kannada"),
)

DEFAULT_LANGUAGE = "en"
SUPPORTED_CODES = frozenset(l.code for l in LANGUAGES)
_BY_CODE: dict[str, Language] = {l.code: l for l in LANGUAGES}


# ── Per-request context var ────────────────────────────────────────────────

# Set by LanguageMiddleware. Anything in the request lifecycle (services,
# agents, ledger) can read this without having to thread `language` through
# every signature.
current_language: contextvars.ContextVar[str] = contextvars.ContextVar(
    "aos_language", default=DEFAULT_LANGUAGE,
)


def get_language() -> str:
    """FastAPI-style dependency / utility for callers that prefer functions."""
    return current_language.get()


# ── Header parsing ─────────────────────────────────────────────────────────

def parse_accept_language(header: Optional[str], *, default: str = DEFAULT_LANGUAGE) -> str:
    """Pick the best supported language from an `Accept-Language` header.

    Spec-compliant enough for production:
      - splits on commas
      - reads optional `;q=` quality factors (default 1.0)
      - matches by primary subtag (so `hi-IN` and `hi` both resolve to "hi")
      - sorts by descending quality and returns the first supported code
      - falls back to *default* (or the global DEFAULT_LANGUAGE) if none match.

    >>> parse_accept_language("hi-IN, en;q=0.5")
    'hi'
    >>> parse_accept_language("ja, fr;q=0.9, ta;q=0.4")
    'ta'
    >>> parse_accept_language(None)
    'en'
    """
    if not header:
        return default

    candidates: list[tuple[float, str]] = []
    for raw in header.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if ";" in raw:
            tag, *params = (p.strip() for p in raw.split(";"))
            q = 1.0
            for p in params:
                if p.startswith("q="):
                    try:
                        q = float(p[2:])
                    except ValueError:
                        q = 0.0
            if q <= 0:
                continue
        else:
            tag, q = raw, 1.0
        primary = tag.split("-", 1)[0].lower()
        if primary in SUPPORTED_CODES:
            candidates.append((q, primary))

    if not candidates:
        return default
    # Stable: highest q first, ties keep header order
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def normalize(code: Optional[str]) -> str:
    """Coerce an arbitrary code to a supported one; default if not in catalogue."""
    if not code:
        return DEFAULT_LANGUAGE
    primary = code.split("-", 1)[0].lower()
    return primary if primary in SUPPORTED_CODES else DEFAULT_LANGUAGE


def language(code: Optional[str]) -> Language:
    return _BY_CODE[normalize(code)]


# ── LLM prompt helper ──────────────────────────────────────────────────────

_DIRECTIVE_TEMPLATE = (
    "\n\n# Response language\n"
    "Respond to the user in {native} ({english}, {script} script). "
    "Keep all proper nouns, numerical figures, ISO codes, and currency "
    "symbols (₹, INR) in their canonical form — do NOT transliterate "
    "amounts, account codes, GSTINs, PANs, or HSN codes. "
    "Numerical values must use Latin digits and Indian lakh/crore "
    "grouping (e.g. 12,50,000). Keep tool names and JSON keys in English."
)


def with_language_directive(system_prompt: str, code: Optional[str]) -> str:
    """Append a 'respond in <lang>' directive to a system prompt.

    The directive is a no-op for English (since the prompt is already in
    English and any extra text would just bloat the cache key).
    """
    lang = language(code)
    if lang.code == DEFAULT_LANGUAGE:
        return system_prompt
    return system_prompt + _DIRECTIVE_TEMPLATE.format(
        native=lang.native,
        english=lang.english,
        script=lang.script_hint,
    )


def supported_summary() -> Iterable[dict[str, str]]:
    """Cheap JSON summary of supported languages for /api/v1/meta endpoints."""
    return (
        {"code": l.code, "native": l.native, "english": l.english, "bcp47": l.bcp47}
        for l in LANGUAGES
    )
