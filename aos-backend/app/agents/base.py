"""
AOS Agent Base — common types and BaseAgent class.

Design:
  - Agents are stateless planners that convert user intent into a plan of tool calls.
  - Tools are deterministic functions registered with the ToolRegistry.
  - Every agent action is evaluated against the Policy Engine BEFORE execution.
  - Every agent action is logged to the audit trail AFTER execution.
  - Agents never talk to the database directly; they only call tools.

The probabilistic layer (LLM) produces *intent + plan*.
The deterministic layer (tools + ledger) *executes*.
"""

from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional


# ---- Agent Context -----------------------------------------------------------

@dataclass
class AgentContext:
    """The per-turn context passed to an agent.

    Contains authenticated user info, org scope, conversation history,
    and a correlation id for tracing.
    """

    org_id: uuid.UUID
    user_id: uuid.UUID
    user_role: str
    session_id: Optional[uuid.UUID] = None
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    channel: str = "web"  # web / whatsapp / voice / email / api
    language: str = "en"
    history: list[dict[str, Any]] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Guardrails for this turn
    max_tool_calls: int = 10
    max_tokens: int = 8000
    idempotency_key: Optional[str] = None


# ---- Tool Types --------------------------------------------------------------

@dataclass
class ToolCall:
    """A single tool invocation planned or executed by an agent."""

    id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    reasoning: Optional[str] = None
    confidence: Optional[Decimal] = None
    idempotency_key: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "reasoning": self.reasoning,
            "confidence": float(self.confidence) if self.confidence is not None else None,
            "idempotency_key": self.idempotency_key,
        }


@dataclass
class ToolResult:
    """The outcome of a tool invocation."""

    tool_call_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    requires_approval: bool = False
    approval_request_id: Optional[uuid.UUID] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "requires_approval": self.requires_approval,
            "approval_request_id": str(self.approval_request_id) if self.approval_request_id else None,
        }


# ---- Agent Result ------------------------------------------------------------

@dataclass
class AgentResult:
    """The final structured output of an agent turn."""

    agent_name: str
    intent: Optional[str] = None
    response_text: str = ""
    structured_output: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    confidence: Optional[Decimal] = None
    requires_human: bool = False
    approval_request_ids: list[uuid.UUID] = field(default_factory=list)
    error: Optional[str] = None
    tokens_used: int = 0
    latency_ms: int = 0
    model_used: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "intent": self.intent,
            "response_text": self.response_text,
            "structured_output": self.structured_output,
            "tool_calls": [t.to_dict() for t in self.tool_calls],
            "tool_results": [t.to_dict() for t in self.tool_results],
            "confidence": float(self.confidence) if self.confidence is not None else None,
            "requires_human": self.requires_human,
            "approval_request_ids": [str(x) for x in self.approval_request_ids],
            "error": self.error,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "model_used": self.model_used,
        }


# ---- BaseAgent ---------------------------------------------------------------

class BaseAgent(abc.ABC):
    """Abstract base for all AOS agents.

    Concrete agents override:
      - name, description, domain
      - supported_intents
      - system_prompt
      - plan() — produces a list of ToolCall from context + user message
      - (optional) post_process() — formats final response
    """

    name: str = "base"
    description: str = "Abstract base agent"
    domain: str = "general"
    version: str = "0.1.0"
    supported_intents: list[str] = []
    system_prompt: str = "You are an AOS agent. Follow instructions precisely."

    # Which tools this agent is allowed to call (by name). Empty = all registered.
    allowed_tools: list[str] = []

    @abc.abstractmethod
    async def plan(
        self,
        user_message: str,
        context: AgentContext,
    ) -> list[ToolCall]:
        """Return a plan of tool calls given user intent."""
        raise NotImplementedError

    async def post_process(
        self,
        context: AgentContext,
        tool_calls: list[ToolCall],
        tool_results: list[ToolResult],
    ) -> str:
        """Default post-processor returns a terse summary of tool outcomes.

        Localised for the 8 supported UI languages — falls back to English
        for anything else. Used when the LLM didn't produce response text
        (e.g. tool-only agents or planning failures).
        """
        from app.core.i18n import normalize  # local import to avoid cycles

        ok = sum(1 for r in tool_results if r.success)
        fail = len(tool_results) - ok
        pending = sum(1 for r in tool_results if r.requires_approval)

        # Per-language phrase parts: (no_action, completed, awaiting, failed)
        phrases: dict[str, tuple[str, str, str, str]] = {
            "en": ("No actions taken.", "{n} completed",      "{n} awaiting approval", "{n} failed"),
            "hi": ("कोई कार्य नहीं हुआ।", "{n} पूर्ण",          "{n} अनुमोदन प्रतीक्षित", "{n} विफल"),
            "bn": ("কোন কাজ হয়নি।",   "{n} সম্পন্ন",          "{n} অনুমোদনের অপেক্ষায়", "{n} ব্যর্থ"),
            "ta": ("எந்த நடவடிக்கையும் இல்லை.", "{n} முடிந்தது", "{n} அனுமதிக்கு நிலுவை",  "{n} தோல்வி"),
            "te": ("చర్యలు తీసుకోబడలేదు.", "{n} పూర్తి",        "{n} అనుమతి పెండింగ్",     "{n} విఫలం"),
            "mr": ("कोणतीही कृती झाली नाही.", "{n} पूर्ण",        "{n} मंजुरी प्रलंबित",      "{n} अयशस्वी"),
            "gu": ("કોઈ ક્રિયા થઈ નથી.",  "{n} પૂર્ણ",            "{n} મંજૂરી બાકી",          "{n} નિષ્ફળ"),
            "kn": ("ಯಾವುದೇ ಕ್ರಮ ತೆಗೆದುಕೊಂಡಿಲ್ಲ.", "{n} ಪೂರ್ಣ",  "{n} ಅನುಮೋದನೆ ಬಾಕಿ",   "{n} ವಿಫಲ"),
        }
        none_msg, done_t, pend_t, fail_t = phrases.get(normalize(context.language), phrases["en"])

        if not tool_results:
            return none_msg
        parts = [done_t.format(n=ok)]
        if pending:
            parts.append(pend_t.format(n=pending))
        if fail:
            parts.append(fail_t.format(n=fail))
        return ", ".join(parts) + "."

    def can_handle_intent(self, intent: str) -> bool:
        return intent in self.supported_intents
