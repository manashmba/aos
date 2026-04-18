"""
Notification Service — one API for sending a message across multiple
channels (WhatsApp via the aos-whatsapp-bot bridge, email, and in-app).

Channels fail soft: if a provider misbehaves, we log and continue. The
service never raises on a single-channel failure — callers get a per-
channel outcome map.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from app.core.config import get_settings
from app.integrations.email import EmailMessage
from app.integrations.registry import get_integration
from app.integrations.whatsapp import WhatsAppMessage

log = logging.getLogger(__name__)


class NotificationChannel(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    IN_APP = "in_app"


@dataclass
class NotificationRequest:
    subject: str
    body: str
    channels: list[NotificationChannel]
    to_phone: Optional[str] = None
    to_email: Optional[list[str]] = None
    template: Optional[str] = None
    template_params: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class NotificationService:
    def __init__(self, bot_url: Optional[str] = None, service_token: Optional[str] = None):
        s = get_settings()
        self.bot_url = bot_url or getattr(s, "whatsapp_bot_url", None)
        self.service_token = service_token or getattr(s, "whatsapp_bot_token", None)

    async def send(self, req: NotificationRequest) -> dict[str, Any]:
        outcomes: dict[str, Any] = {}
        for ch in req.channels:
            try:
                if ch == NotificationChannel.WHATSAPP:
                    outcomes["whatsapp"] = await self._send_whatsapp(req)
                elif ch == NotificationChannel.EMAIL:
                    outcomes["email"] = await self._send_email(req)
                elif ch == NotificationChannel.IN_APP:
                    outcomes["in_app"] = {"status": "queued", "note": "in-app via events bus"}
            except Exception as e:  # noqa: BLE001
                log.exception("notification channel %s failed", ch.value)
                outcomes[ch.value] = {"status": "failed", "error": str(e)}
        return outcomes

    async def _send_whatsapp(self, req: NotificationRequest) -> dict[str, Any]:
        if not req.to_phone:
            return {"status": "skipped", "reason": "no_phone"}

        # Prefer the HTTP bridge if configured; fall back to the in-process
        # integration (mock in dev).
        if self.bot_url:
            return await self._call_bot(req)

        provider = get_integration("whatsapp")
        if req.template:
            msg = WhatsAppMessage(
                to=req.to_phone,
                message_type="template",
                template_name=req.template,
                template_params=req.template_params,
            )
        else:
            msg = WhatsAppMessage(to=req.to_phone, message_type="text", body=req.body)
        return await provider.send(msg)

    async def _call_bot(self, req: NotificationRequest) -> dict[str, Any]:
        assert req.to_phone
        path = "/notify/template" if req.template else "/notify/text"
        payload: dict[str, Any] = {"to": req.to_phone}
        if req.template:
            payload["template"] = req.template
            payload["params"] = req.template_params
        else:
            payload["body"] = req.body

        headers = {}
        if self.service_token:
            headers["Authorization"] = f"Bearer {self.service_token}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{self.bot_url.rstrip('/')}{path}", json=payload, headers=headers)
            r.raise_for_status()
            return r.json()

    async def _send_email(self, req: NotificationRequest) -> dict[str, Any]:
        if not req.to_email:
            return {"status": "skipped", "reason": "no_email"}
        provider = get_integration("email")
        return await provider.send(
            EmailMessage(
                to=req.to_email,
                subject=req.subject,
                body_text=req.body,
                template=req.template,
                template_vars={"params": req.template_params, **req.metadata},
            )
        )
