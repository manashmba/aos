"""Tally integration adapter (XML export/import)."""
from app.integrations.tally.protocol import TallyProvider, TallyVoucher, TallyLedger
from app.integrations.tally.mock import MockTallyProvider

__all__ = ["TallyProvider", "TallyVoucher", "TallyLedger", "MockTallyProvider"]
