"""Mock Tally provider — generates XML in memory."""

from __future__ import annotations

from datetime import date
from typing import Any
from xml.sax.saxutils import escape

from app.integrations.tally.protocol import TallyLedger, TallyVoucher


class MockTallyProvider:
    def __init__(self) -> None:
        self.pushed_vouchers: list[TallyVoucher] = []
        self.pushed_ledgers: list[TallyLedger] = []

    async def push_voucher(self, voucher: TallyVoucher) -> dict[str, Any]:
        self.pushed_vouchers.append(voucher)
        return {"voucher_number": voucher.voucher_number, "status": "accepted"}

    async def push_ledger(self, ledger: TallyLedger) -> dict[str, Any]:
        self.pushed_ledgers.append(ledger)
        return {"name": ledger.name, "status": "accepted"}

    async def fetch_vouchers(self, from_date: date, to_date: date) -> list[TallyVoucher]:
        return [v for v in self.pushed_vouchers if from_date <= v.voucher_date <= to_date]

    async def export_xml(self, vouchers: list[TallyVoucher]) -> str:
        parts = ["<ENVELOPE>", "<HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>", "<BODY><IMPORTDATA><REQUESTDATA>"]
        for v in vouchers:
            parts.append(f'<TALLYMESSAGE><VOUCHER VCHTYPE="{escape(v.voucher_type)}" ACTION="Create">')
            parts.append(f"<DATE>{v.voucher_date.strftime('%Y%m%d')}</DATE>")
            parts.append(f"<VOUCHERNUMBER>{escape(v.voucher_number)}</VOUCHERNUMBER>")
            parts.append(f"<NARRATION>{escape(v.narration or '')}</NARRATION>")
            for e in v.entries:
                amt = e.get("amount", 0)
                is_debit = e.get("debit") is not None or (e.get("direction") == "debit")
                amount_str = f"-{amt}" if is_debit else f"{amt}"
                parts.append("<ALLLEDGERENTRIES.LIST>")
                parts.append(f"<LEDGERNAME>{escape(str(e.get('ledger', '')))}</LEDGERNAME>")
                parts.append(f"<AMOUNT>{amount_str}</AMOUNT>")
                parts.append("</ALLLEDGERENTRIES.LIST>")
            parts.append("</VOUCHER></TALLYMESSAGE>")
        parts.append("</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")
        return "".join(parts)
