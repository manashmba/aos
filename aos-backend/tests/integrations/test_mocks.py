"""Smoke tests for mock integration providers."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from app.integrations.banking import MockBankProvider, PaymentInstruction, is_valid_ifsc
from app.integrations.email import EmailMessage, MockEmailProvider
from app.integrations.gst import (
    EInvoiceRequest,
    MockGSTProvider,
    is_intra_state,
    is_valid_gstin,
)
from app.integrations.ocr import MockOCRProvider
from app.integrations.tally import MockTallyProvider, TallyVoucher
from app.integrations.whatsapp import MockWhatsAppProvider, WhatsAppMessage


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if not asyncio.iscoroutine(coro) else asyncio.run(coro)


def test_gstin_validation():
    assert is_valid_gstin("27AAAPL1234C1Z5")
    assert not is_valid_gstin("INVALID")
    assert is_intra_state("27AAAPL1234C1Z5", "27BBBPL9876D1Z3")
    assert not is_intra_state("27AAAPL1234C1Z5", "29CCCPL5555E1Z1")


def test_ifsc_validation():
    assert is_valid_ifsc("HDFC0001234")
    assert not is_valid_ifsc("BADIFSC")


def test_mock_whatsapp():
    async def go():
        p = MockWhatsAppProvider()
        r = await p.send(WhatsAppMessage(to="+919999999999", message_type="text", body="hi"))
        assert r["status"] == "accepted"
        assert len(p.sent) == 1

    asyncio.run(go())


def test_mock_gst_irn_deterministic():
    async def go():
        p = MockGSTProvider()
        req = EInvoiceRequest(
            invoice_number="INV-1",
            invoice_date=date(2025, 4, 10),
            supplier_gstin="27AAAPL1234C1Z5",
            buyer_gstin="29BBBPL9876D1Z3",
            buyer_name="Buyer Co",
            buyer_state_code="29",
            line_items=[],
            subtotal=Decimal("1000"),
            cgst=Decimal("0"), sgst=Decimal("0"), igst=Decimal("180"),
            total=Decimal("1180"),
        )
        r1 = await p.generate_irn(req)
        r2 = await p.generate_irn(req)
        assert r1.irn == r2.irn  # deterministic by (gstin, number, date, total)
        assert len(r1.irn) == 64

    asyncio.run(go())


def test_mock_bank_idempotent_payment():
    async def go():
        p = MockBankProvider(starting_balance=Decimal("100000"))
        pi = PaymentInstruction(
            idempotency_key="pay-1",
            beneficiary_name="Vendor",
            beneficiary_account="123456789012",
            beneficiary_ifsc="HDFC0001234",
            amount=Decimal("5000"),
            mode="neft",
        )
        r1 = await p.initiate_payment(pi)
        r2 = await p.initiate_payment(pi)
        assert r1.utr == r2.utr
        assert await p.current_balance("x") == Decimal("95000")

    asyncio.run(go())


def test_mock_bank_insufficient_balance():
    async def go():
        p = MockBankProvider(starting_balance=Decimal("100"))
        r = await p.initiate_payment(PaymentInstruction(
            idempotency_key="pay-big",
            beneficiary_name="V",
            beneficiary_account="123456789012",
            beneficiary_ifsc="HDFC0001234",
            amount=Decimal("1000"),
            mode="imps",
        ))
        assert r.status == "failed"
        assert r.raw.get("reason") == "insufficient_balance"

    asyncio.run(go())


def test_mock_email_send():
    async def go():
        p = MockEmailProvider()
        r = await p.send(EmailMessage(to=["a@b.com"], subject="hi", body_text="hello"))
        assert r["status"] == "queued"

    asyncio.run(go())


def test_mock_tally_xml_roundtrip():
    async def go():
        p = MockTallyProvider()
        v = TallyVoucher(
            voucher_type="Sales",
            voucher_number="INV-1",
            voucher_date=date(2025, 4, 1),
            narration="Test",
            entries=[
                {"ledger": "Acme & Co", "amount": "1000", "direction": "debit"},
                {"ledger": "Sales", "amount": "1000", "direction": "credit"},
            ],
        )
        await p.push_voucher(v)
        xml = await p.export_xml([v])
        assert "<VOUCHER" in xml
        assert "Acme &amp; Co" in xml  # escaping
        fetched = await p.fetch_vouchers(date(2025, 4, 1), date(2025, 4, 30))
        assert len(fetched) == 1

    asyncio.run(go())


def test_mock_ocr_invoice():
    async def go():
        p = MockOCRProvider()
        r = await p.extract_invoice(b"fake-pdf")
        assert r.confidence > 0.9
        assert r.vendor_gstin and is_valid_gstin(r.vendor_gstin)

    asyncio.run(go())
