"""WhatsApp adapter protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Protocol


@dataclass
class WhatsAppMessage:
    to: str                       # E.164 phone number
    message_type: str             # text | template | media | interactive
    body: Optional[str] = None
    template_name: Optional[str] = None
    template_params: list[str] = field(default_factory=list)
    media_url: Optional[str] = None
    buttons: list[dict[str, str]] = field(default_factory=list)
    locale: str = "en"


class WhatsAppProvider(Protocol):
    async def send(self, message: WhatsAppMessage) -> dict[str, Any]:
        """Send a message. Returns {message_id, status, provider_raw}."""

    async def verify_webhook(self, token: str, challenge: str) -> Optional[str]:
        """Return challenge if valid verify token, else None."""

    async def parse_webhook(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse provider webhook into normalized inbound events."""
