"""
AOS LLM Client — thin wrapper over Anthropic (primary) and OpenAI (fallback).

Responsibilities:
  - Uniform chat/completion interface with structured JSON output.
  - Automatic fallback from primary to secondary on hard failure.
  - Token + latency accounting.
  - Prompt caching hooks (Anthropic) for static system instructions.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.config import get_settings

try:  # soft imports so module loads even if SDK absent
    from anthropic import AsyncAnthropic
except Exception:  # pragma: no cover
    AsyncAnthropic = None  # type: ignore

try:
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore


@dataclass
class LLMResponse:
    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    raw: Any = None


class LLMClient:
    """Single entry point the rest of AOS uses to talk to LLMs."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._anthropic = (
            AsyncAnthropic(api_key=self.settings.anthropic_api_key)
            if AsyncAnthropic and self.settings.anthropic_api_key
            else None
        )
        self._openai = (
            AsyncOpenAI(api_key=self.settings.openai_api_key)
            if AsyncOpenAI and self.settings.openai_api_key
            else None
        )

    # ---- Primary: Anthropic (Claude) ----------------------------------------

    async def complete_anthropic(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        model: Optional[str] = None,
    ) -> LLMResponse:
        if self._anthropic is None:
            raise RuntimeError("Anthropic client not configured")

        started = time.perf_counter()
        resp = await self._anthropic.messages.create(
            model=model or self.settings.primary_llm_model,
            system=system,
            messages=messages,
            tools=tools or [],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        # Extract text + tool uses
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in getattr(resp, "content", []) or []:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(getattr(block, "text", ""))
            elif btype == "tool_use":
                tool_calls.append({
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input": getattr(block, "input", {}),
                })

        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text="".join(text_parts),
            model=getattr(resp, "model", model or self.settings.primary_llm_model),
            tokens_in=getattr(usage, "input_tokens", 0) if usage else 0,
            tokens_out=getattr(usage, "output_tokens", 0) if usage else 0,
            latency_ms=latency_ms,
            tool_calls=tool_calls,
            raw=resp,
        )

    # ---- Fallback: OpenAI ---------------------------------------------------

    async def complete_openai(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        model: Optional[str] = None,
    ) -> LLMResponse:
        if self._openai is None:
            raise RuntimeError("OpenAI client not configured")

        oai_messages = [{"role": "system", "content": system}] + messages
        oai_tools = [{"type": "function", "function": t} for t in (tools or [])]

        started = time.perf_counter()
        resp = await self._openai.chat.completions.create(
            model=model or self.settings.fallback_llm_model,
            messages=oai_messages,
            tools=oai_tools or None,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        choice = resp.choices[0]
        text = choice.message.content or ""
        tool_calls: list[dict[str, Any]] = []
        for tc in (choice.message.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            tool_calls.append({"id": tc.id, "name": tc.function.name, "input": args})

        usage = resp.usage
        return LLMResponse(
            text=text,
            model=resp.model,
            tokens_in=getattr(usage, "prompt_tokens", 0) if usage else 0,
            tokens_out=getattr(usage, "completion_tokens", 0) if usage else 0,
            latency_ms=latency_ms,
            tool_calls=tool_calls,
            raw=resp,
        )

    # ---- Unified entry point with fallback ----------------------------------

    async def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Try primary, fall back to secondary on failure."""
        try:
            if self._anthropic is not None:
                return await self.complete_anthropic(
                    system=system,
                    messages=messages,
                    tools=tools,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
        except Exception:
            pass

        if self._openai is None:
            raise RuntimeError("No LLM provider configured")
        return await self.complete_openai(
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )
