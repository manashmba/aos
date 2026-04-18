"""Email provider protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


@dataclass
class EmailMessage:
    to: list[str]
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    reply_to: Optional[str] = None
    attachments: list[dict[str, Any]] = field(default_factory=list)  # {filename, content_b64, content_type}
    template: Optional[str] = None
    template_vars: dict[str, Any] = field(default_factory=dict)


class EmailProvider(Protocol):
    async def send(self, message: EmailMessage) -> dict[str, Any]: ...
