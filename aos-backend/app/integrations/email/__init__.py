"""Transactional email adapter."""
from app.integrations.email.protocol import EmailMessage, EmailProvider
from app.integrations.email.mock import MockEmailProvider

__all__ = ["EmailMessage", "EmailProvider", "MockEmailProvider"]
