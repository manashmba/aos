"""Mock email provider — records sent messages in memory."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.integrations.email.protocol import EmailMessage


class MockEmailProvider:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send(self, message: EmailMessage) -> dict[str, Any]:
        record = {
            "message_id": f"mock_{uuid.uuid4().hex[:12]}",
            "to": message.to,
            "subject": message.subject,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "template": message.template,
            "has_html": bool(message.body_html),
            "attachments": [a.get("filename") for a in message.attachments],
        }
        self.sent.append(record)
        return {"message_id": record["message_id"], "status": "queued"}
