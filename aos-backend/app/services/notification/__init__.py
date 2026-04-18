"""Notification service — fan out alerts across WhatsApp, email, in-app."""
from app.services.notification.service import (
    NotificationChannel,
    NotificationRequest,
    NotificationService,
)

__all__ = ["NotificationChannel", "NotificationRequest", "NotificationService"]
