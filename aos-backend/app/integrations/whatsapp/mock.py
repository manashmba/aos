"""In-memory mock WhatsApp provider for local dev + tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.integrations.whatsapp.protocol import WhatsAppMessage


class MockWhatsAppProvider:
    def __init__(self, verify_token: str = "aos-dev"):
        self.verify_token = verify_token
        self.sent: list[dict[str, Any]] = []

    async def send(self, message: WhatsAppMessage) -> dict[str, Any]:
        record = {
            "message_id": f"mock_{uuid.uuid4().hex[:12]}",
            "status": "accepted",
            "to": message.to,
            "type": message.message_type,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "body": message.body,
                "template": message.template_name,
                "params": message.template_params,
                "media_url": message.media_url,
                "buttons": message.buttons,
            },
        }
        self.sent.append(record)
        return record

    async def verify_webhook(self, token: str, challenge: str) -> Optional[str]:
        return challenge if token == self.verify_token else None

    async def parse_webhook(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Accept a simple `{from, text, timestamp}` shape for tests."""
        events: list[dict[str, Any]] = []
        for entry in payload.get("messages", []):
            events.append({
                "provider_message_id": entry.get("id", f"mock_{uuid.uuid4().hex[:8]}"),
                "from": entry.get("from"),
                "text": entry.get("text", {}).get("body") if isinstance(entry.get("text"), dict) else entry.get("text"),
                "timestamp": entry.get("timestamp"),
                "type": entry.get("type", "text"),
            })
        return events
