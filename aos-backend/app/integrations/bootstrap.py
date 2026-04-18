"""
Bootstrap integrations — called from the FastAPI lifespan.

Wires mock providers in the dev environment; real providers will be wired
based on settings in later modules.
"""

from __future__ import annotations

import logging

from app.integrations.banking import MockBankProvider
from app.integrations.email import MockEmailProvider
from app.integrations.gst import MockGSTProvider
from app.integrations.ocr import MockOCRProvider
from app.integrations.registry import register_integration
from app.integrations.tally import MockTallyProvider
from app.integrations.whatsapp import MockWhatsAppProvider

log = logging.getLogger(__name__)


def bootstrap_integrations() -> None:
    """Idempotently register default (mock) providers."""
    register_integration("whatsapp", MockWhatsAppProvider())
    register_integration("gst", MockGSTProvider())
    register_integration("bank", MockBankProvider())
    register_integration("email", MockEmailProvider())
    register_integration("tally", MockTallyProvider())
    register_integration("ocr", MockOCRProvider())
    log.info("Integrations bootstrapped: whatsapp, gst, bank, email, tally, ocr (all mock)")
